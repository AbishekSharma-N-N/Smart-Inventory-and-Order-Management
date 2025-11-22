from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app import models, schemas
from app.services.service_bus import publish_order_event
from app.auth import require_role

router = APIRouter(prefix="/orders", tags=["Orders"])

# ✅ Admin + Warehouse can create orders
@router.post("/", response_model=schemas.OrderOut, dependencies=[Depends(require_role("admin", "warehouse"))])
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    # Create order record
    new_order = models.Order(
        warehouse_id=order.warehouse_id,
        status="created"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Insert order items
    for item in order.items:
        order_item = models.OrderItem(
            order_id=new_order.order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(order_item)
    db.commit()

    # Fetch inserted items
    items = db.query(models.OrderItem).filter(
        models.OrderItem.order_id == new_order.order_id
    ).all()

    # Safe JSON event
    event = {
        "order_id": new_order.order_id,
        "warehouse_id": new_order.warehouse_id,
        "items": [
            {"product_id": i.product_id, "quantity": i.quantity, "price": float(i.price)}
            for i in items
        ]
    }

    publish_order_event(event)

    return {
        "order_id": new_order.order_id,
        "warehouse_id": new_order.warehouse_id,
        "status": new_order.status,
        "items": [
            {
                "order_item_id": i.order_item_id,
                "product_id": i.product_id,
                "quantity": i.quantity,
                "price": float(i.price)
            } for i in items
        ]
    }

# ✅ Admin only can cancel/delete orders
@router.delete("/{order_id}", dependencies=[Depends(require_role("admin"))])
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": f"Order {order_id} cancelled successfully."}
