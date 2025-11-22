from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app import models, schemas
from app.auth import verify_token, require_role  # ✅ Include role-based helper

router = APIRouter(prefix="/products", tags=["Products"])

# ✅ Admin-only: Create a new product
@router.post(
    "/",
    response_model=schemas.ProductOut,
    dependencies=[Depends(require_role("admin"))]  # Protect route for admin
)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    new_product = models.Product(**product.dict())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


# ✅ Admin & Warehouse: View all products
@router.get(
    "/",
    response_model=list[schemas.ProductOut],
    dependencies=[Depends(require_role("warehouse"))]  # Warehouse or higher
)
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()


# ✅ Admin-only: Delete a product
@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))]
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


# ✅ Admin-only: Update a product
@router.put(
    "/{product_id}",
    response_model=schemas.ProductOut,
    dependencies=[Depends(require_role("admin"))]
)
def update_product(product_id: int, updated_data: schemas.ProductCreate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in updated_data.dict().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product
