import os
import json
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()

# Connection details
CONN_STR = os.getenv("SERVICE_BUS_CONNECTION_STRING")

# Queue names
ORDERS_QUEUE = os.getenv("ORDERS_QUEUE_NAME", "orders-queue")
CONFIRMATION_QUEUE = os.getenv("CONFIRMATION_QUEUE_NAME", "order-confirmation-queue")


def send_message(queue_name: str, message_data: dict):
    """Generic function to send JSON messages to any queue."""
    with ServiceBusClient.from_connection_string(CONN_STR) as client:
        sender = client.get_queue_sender(queue_name)
        with sender:
            message = ServiceBusMessage(json.dumps(message_data))
            sender.send_messages(message)
            print(f"📨 Sent to {queue_name}: {json.dumps(message_data)}")


def publish_order_event(order_event: dict):
    """FastAPI /orders uses this to send order messages."""
    send_message(ORDERS_QUEUE, order_event)
