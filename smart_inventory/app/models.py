from sqlalchemy import Column, Integer, String, Text, DECIMAL, DateTime, Enum, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.db import Base
import enum


class OrderStatus(str, enum.Enum):
    created = "created"
    reserved = "reserved"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
    failed = "failed"


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    contact = Column(String(120))
    region = Column(String(60))


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(40), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text)
    category = Column(String(80))
    price = Column(DECIMAL(10,2), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"))
    image_url = Column(String(400))

    supplier = relationship("Supplier")


class Warehouse(Base):
    __tablename__ = "warehouses"

    warehouse_id = Column(Integer, primary_key=True, index=True)
    code = Column(String(16), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    location = Column(String(120))
    capacity = Column(Integer)
    manager = Column(String(120))
    region = Column(String(60))


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=False)
    quantity = Column(Integer, default=0)
    last_updated = Column(TIMESTAMP)

    product = relationship("Product")
    warehouse = relationship("Warehouse")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True)
    ext_order_id = Column(String(40), unique=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.created)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    invoice_blob = Column(String(400))


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(10,2), nullable=False)
