from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app import models, schemas
from app.auth import require_role

router = APIRouter(prefix="/inventory", tags=["Inventory"])

# ✅ Admin + Warehouse can add inventory
@router.post("/", response_model=schemas.InventoryOut, dependencies=[Depends(require_role("admin", "warehouse"))])
def add_inventory(item: schemas.InventoryCreate, db: Session = Depends(get_db)):
    new_item = models.Inventory(**item.dict())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

# ✅ Admin + Warehouse can view inventory
@router.get("/", response_model=list[schemas.InventoryOut], dependencies=[Depends(require_role("admin", "warehouse"))])
def get_inventory(db: Session = Depends(get_db)):
    return db.query(models.Inventory).all()

# ✅ Admin + Warehouse can update inventory
@router.put("/{inv_id}", response_model=schemas.InventoryOut, dependencies=[Depends(require_role("admin", "warehouse"))])
def update_inventory(inv_id: int, item: schemas.InventoryCreate, db: Session = Depends(get_db)):
    inv = db.query(models.Inventory).filter(models.Inventory.inventory_id == inv_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    inv.product_id = item.product_id
    inv.warehouse_id = item.warehouse_id
    inv.quantity = item.quantity
    db.commit()
    db.refresh(inv)
    return inv

# ✅ Admin + Warehouse can check inventory by warehouse
@router.get("/warehouse/{warehouse_id}", response_model=list[schemas.InventoryOut], dependencies=[Depends(require_role("admin", "warehouse"))])
def inventory_by_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    return db.query(models.Inventory).filter(models.Inventory.warehouse_id == warehouse_id).all()

# ✅ Admin + Warehouse can check inventory by product
@router.get("/product/{product_id}", response_model=list[schemas.InventoryOut], dependencies=[Depends(require_role("admin", "warehouse"))])
def inventory_by_product(product_id: int, db: Session = Depends(get_db)):
    return db.query(models.Inventory).filter(models.Inventory.product_id == product_id).all()
