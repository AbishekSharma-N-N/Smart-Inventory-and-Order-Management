from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SupplierCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    region: Optional[str] = None


class SupplierOut(SupplierCreate):
    supplier_id: int

    class Config:
        orm_mode = True

class ProductCreate(BaseModel):
    sku: str
    name: str
    description: str | None = None
    category: str | None = None
    price: float
    supplier_id: int | None = None

class ProductOut(ProductCreate):
    product_id: int

    class Config:
        orm_mode = True

class WarehouseCreate(BaseModel):
    code: str
    name: str
    location: Optional[str] = None
    capacity: Optional[int] = None
    manager: Optional[str] = None
    region: Optional[str] = None

class WarehouseOut(WarehouseCreate):
    warehouse_id: int
    
    class Config:
        orm_mode = True

class InventoryCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int

class InventoryOut(InventoryCreate):
    inventory_id: int
    last_updated: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderCreate(BaseModel):
    warehouse_id: int
    items: List[OrderItemCreate]

class OrderItemOut(OrderItemCreate):
    order_item_id: int

    class Config:
        orm_mode = True

class OrderOut(BaseModel):
    order_id: int
    warehouse_id: int
    status: str
    items: List[OrderItemOut]

    class Config:
        orm_mode = True
