from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app import models, schemas
from app.auth import require_role

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

# ✅ Admin only
@router.post("/", response_model=schemas.SupplierOut, dependencies=[Depends(require_role("admin"))])
def create_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db)):
    new_supplier = models.Supplier(**supplier.dict())
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier

# ✅ Admin + Warehouse
@router.get("/", response_model=list[schemas.SupplierOut], dependencies=[Depends(require_role("admin", "warehouse"))])
def get_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).all()
