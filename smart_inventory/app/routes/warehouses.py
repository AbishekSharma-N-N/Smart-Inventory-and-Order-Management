from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app import models, schemas
from app.auth import require_role

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])

# ✅ Admin only
@router.post("/", response_model=schemas.WarehouseOut, dependencies=[Depends(require_role("admin"))])
def create_warehouse(warehouse: schemas.WarehouseCreate, db: Session = Depends(get_db)):
    new_warehouse = models.Warehouse(**warehouse.dict())
    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)
    return new_warehouse

# ✅ Admin + Warehouse
@router.get("/", response_model=list[schemas.WarehouseOut], dependencies=[Depends(require_role("admin", "warehouse"))])
def get_warehouses(db: Session = Depends(get_db)):
    return db.query(models.Warehouse).all()
