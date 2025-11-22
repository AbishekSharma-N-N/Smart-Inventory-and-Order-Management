import azure.functions as func
import logging
import json
from sqlalchemy import create_engine, text
import os
import certifi
from fpdf import FPDF
from azure.storage.blob import BlobServiceClient
from io import BytesIO
from datetime import datetime
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# ---------------- ENVIRONMENT CONFIG ----------------
DATABASE_URL = os.getenv("DATABASE_URL")
SERVICE_BUS_CONN = os.getenv("SERVICE_BUS_CONNECTION_STRING")
BLOB_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# ---------------- DATABASE SETUP ----------------
ssl_args = {"ssl": {"ca": certifi.where()}}
engine = create_engine(DATABASE_URL, connect_args=ssl_args, pool_pre_ping=True, future=True)

# ---------------- BLOB STORAGE SETUP ----------------
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
container_name = "invoices"
try:
    blob_service_client.create_container(container_name)
except Exception:
    pass  # Ignore if already exists

# ---------------- SERVICE BUS CLIENT ----------------
def send_to_confirmation_queue(order_id):
    """Send message to order-confirmation-queue after order processed."""
    message_data = {"order_id": order_id}
    with ServiceBusClient.from_connection_string(SERVICE_BUS_CONN) as client:
        sender = client.get_queue_sender(queue_name="order-confirmation-queue")
        with sender:
            sender.send_messages(ServiceBusMessage(json.dumps(message_data)))
            logging.info(f"📨 Sent confirmation trigger for order_id={order_id}")


# ---------------- AZURE FUNCTION APP ----------------
app = func.FunctionApp()

# ===================================================================
# 🧩 Function 1: Process Order (from orders-queue)
# ===================================================================
@app.service_bus_queue_trigger(
    arg_name="azservicebus",
    queue_name="orders-queue",
    connection="SERVICE_BUS_CONNECTION_STRING"
)
def process_order(azservicebus: func.ServiceBusMessage):
    """Handles new orders: updates inventory and marks order as reserved."""
    body = azservicebus.get_body().decode("utf-8")
    logging.info("📦 Order message received: %s", body)

    try:
        order_event = json.loads(body)
        order_id = order_event["order_id"]
        warehouse_id = order_event["warehouse_id"]
        items = order_event["items"]

        with engine.begin() as conn:
            # Ensure order exists, otherwise insert it
            existing = conn.execute(
                text("SELECT order_id FROM orders WHERE order_id = :oid"),
                {"oid": order_id}
            ).fetchone()

            if not existing:
                conn.execute(
                    text("""
                        INSERT INTO orders (order_id, warehouse_id, status)
                        VALUES (:oid, :wid, 'reserved')
                    """),
                    {"oid": order_id, "wid": warehouse_id}
                )
                logging.info(f"🆕 Inserted new order {order_id}")
            else:
                conn.execute(
                    text("UPDATE orders SET status = 'reserved' WHERE order_id = :oid"),
                    {"oid": order_id}
                )
                logging.info(f"🔄 Updated existing order {order_id} to 'reserved'.")

            # Update inventory for each product
            for item in items:
                conn.execute(
                    text("""
                        UPDATE inventory
                        SET quantity = quantity - :qty
                        WHERE product_id = :pid AND warehouse_id = :wid
                    """),
                    {"qty": item["quantity"], "pid": item["product_id"], "wid": warehouse_id}
                )

            # Insert or update order_items
            for item in items:
                conn.execute(
                    text("""
                        INSERT INTO order_items (order_id, product_id, quantity, price)
                        VALUES (:oid, :pid, :qty, :price)
                        ON DUPLICATE KEY UPDATE quantity = :qty, price = :price
                    """),
                    {
                        "oid": order_id,
                        "pid": item["product_id"],
                        "qty": item["quantity"],
                        "price": item["price"],
                    }
                )

        logging.info(f"✅ Inventory updated and Order {order_id} set to 'reserved'")

        # ✅ After processing, trigger confirmation queue
        send_to_confirmation_queue(order_id)

    except Exception as e:
        logging.error(f"❌ Error in process_order: {str(e)}")
        raise


# ===================================================================
# 🧾 PDF Invoice Generator Class
# ===================================================================
class InvoicePDF(FPDF):
    def __init__(self):
        super().__init__()
        font_dir = os.path.dirname(os.path.abspath(__file__))
        self.add_font("DejaVu", "", os.path.join(font_dir, "DejaVuSans.ttf"), uni=True)
        self.add_font("DejaVu", "B", os.path.join(font_dir, "DejaVuSans-Bold.ttf"), uni=True)
        self.set_font("DejaVu", "", 12)

    def header(self):
        self.set_font("DejaVu", "B", 16)
        self.set_fill_color(44, 62, 80)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, "SMART INVENTORY SOLUTIONS PVT. LTD.", 0, 1, "C", fill=True)
        self.ln(4)

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("DejaVu", "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "Thank you for your business!", 0, 1, "C")
        self.cell(0, 10, "Contact: support@smartinventory.com", 0, 0, "C")


# ===================================================================
# 🧩 Function 2: Confirm Order (from order-confirmation-queue)
# ===================================================================
@app.service_bus_queue_trigger(
    arg_name="azservicebus",
    queue_name="order-confirmation-queue",
    connection="SERVICE_BUS_CONNECTION_STRING"
)
def confirm_order(azservicebus: func.ServiceBusMessage):
    """Handles order confirmation: generates PDF and uploads invoice to Blob Storage."""
    body = azservicebus.get_body().decode("utf-8")
    logging.info("✅ Order confirmation received: %s", body)

    try:
        event = json.loads(body.replace("'", '"'))
        order_id = event["order_id"]

        with engine.begin() as conn:
            # Check if order exists
            order = conn.execute(
                text("SELECT * FROM orders WHERE order_id = :oid"),
                {"oid": order_id}
            ).mappings().first()

            if not order:
                logging.warning(f"⚠️ Order {order_id} not found, skipping invoice.")
                return

            conn.execute(
                text("UPDATE orders SET status = 'confirmed' WHERE order_id = :oid"),
                {"oid": order_id}
            )

            items = conn.execute(
                text("SELECT product_id, quantity, price FROM order_items WHERE order_id = :oid"),
                {"oid": order_id}
            ).mappings().all()

            total_amount = sum(float(i["quantity"]) * float(i["price"]) for i in items)
            conn.execute(
                text("INSERT INTO invoice(order_id, created_at) VALUES (:oid, NOW())"),
                {"oid": order_id}
            )

        # Generate PDF
        pdf = InvoicePDF()
        pdf.add_page()
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"Invoice #: INV-{order_id:04}", 0, 1, "R")
        pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R")
        pdf.ln(5)

        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 10, "Invoice Details", 0, 1)
        pdf.set_font("DejaVu", "", 11)
        pdf.cell(100, 8, f"Order ID: {order_id}", 0, 1)
        pdf.cell(100, 8, f"Warehouse ID: {order['warehouse_id']}", 0, 1)
        pdf.cell(100, 8, "Customer: Syed Saad", 0, 1)
        pdf.ln(8)

        pdf.set_fill_color(41, 128, 185)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(50, 10, "Product ID", 1, 0, "C", True)
        pdf.cell(40, 10, "Quantity", 1, 0, "C", True)
        pdf.cell(50, 10, "Price (₹)", 1, 0, "C", True)
        pdf.cell(50, 10, "Total (₹)", 1, 1, "C", True)

        pdf.set_font("DejaVu", "", 11)
        pdf.set_text_color(0, 0, 0)
        for item in items:
            pid, qty, price = item["product_id"], item["quantity"], item["price"]
            line_total = float(qty) * float(price)
            pdf.cell(50, 10, str(pid), 1, 0, "C")
            pdf.cell(40, 10, str(qty), 1, 0, "C")
            pdf.cell(50, 10, f"{price:.2f}", 1, 0, "C")
            pdf.cell(50, 10, f"{line_total:.2f}", 1, 1, "C")

        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(140, 10, "Grand Total", 1, 0, "R")
        pdf.cell(50, 10, f"₹ {total_amount:.2f}", 1, 1, "C")

        # Upload to Blob
        pdf_bytes = bytes(pdf.output(dest="S"))
        blob_name = f"invoice_order_{order_id}.pdf"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(BytesIO(pdf_bytes), overwrite=True)
        blob_url = blob_client.url

        # Update DB
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE orders SET invoice_blob = :url WHERE order_id = :oid"),
                {"url": blob_url, "oid": order_id}
            )

        logging.info(f"✅ Invoice generated & uploaded: {blob_url}")

    except Exception as e:
        logging.error(f"❌ Error in confirm_order: {str(e)}")
        raise
