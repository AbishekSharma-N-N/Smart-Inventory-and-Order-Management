from fastapi import FastAPI
from app.routes import suppliers, products, warehouses, inventory, orders
from app.routes import auth_router

app = FastAPI(title="Smart Inventory & Order Management API")

# Include routers
app.include_router(auth_router.router)       # ✅ JWT Authentication routes
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(warehouses.router)
app.include_router(inventory.router)
app.include_router(orders.router)


@app.get("/")
def root():
    return {"message": "Smart Inventory & Order Management API is running 🚀"}
