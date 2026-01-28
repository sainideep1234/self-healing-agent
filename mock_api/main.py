"""
Mock Legacy API - Simulates an upstream API that can change schemas.

This API simulates a "legacy" or third-party API that the proxy sits in front of.
It has configurable "modes" to simulate schema changes:

1. STABLE: Returns expected schema (user_id, name, etc.)
2. DRIFTED: Returns changed schema (uid, full_name, etc.)
3. CHAOTIC: Randomly changes between modes

Use this to test the self-healing capabilities of the gateway.
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
from enum import Enum
import random

app = FastAPI(
    title="Mock Legacy API",
    description="Simulated upstream API for testing schema healing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SchemaMode(str, Enum):
    """Schema mode for the mock API."""
    STABLE = "stable"    # Returns expected schema
    DRIFTED = "drifted"  # Returns changed schema
    CHAOTIC = "chaotic"  # Randomly switches


# Current mode (can be changed via API)
current_mode = SchemaMode.STABLE


# ============================================================================
# Mock Data
# ============================================================================

USERS_STABLE = [
    {"user_id": 1, "name": "Alice Johnson", "email": "alice@example.com", "created_at": "2024-01-15T10:30:00Z"},
    {"user_id": 2, "name": "Bob Smith", "email": "bob@example.com", "created_at": "2024-02-20T14:45:00Z"},
    {"user_id": 3, "name": "Charlie Brown", "email": "charlie@example.com", "created_at": "2024-03-10T09:15:00Z"},
]

USERS_DRIFTED = [
    {"uid": 1, "full_name": "Alice Johnson", "email_address": "alice@example.com", "registered_date": "2024-01-15T10:30:00Z"},
    {"uid": 2, "full_name": "Bob Smith", "email_address": "bob@example.com", "registered_date": "2024-02-20T14:45:00Z"},
    {"uid": 3, "full_name": "Charlie Brown", "email_address": "charlie@example.com", "registered_date": "2024-03-10T09:15:00Z"},
]

PRODUCTS_STABLE = [
    {"product_id": 101, "title": "Wireless Headphones", "price": 79.99, "in_stock": True},
    {"product_id": 102, "title": "USB-C Hub", "price": 49.99, "in_stock": True},
    {"product_id": 103, "title": "Mechanical Keyboard", "price": 149.99, "in_stock": False},
]

PRODUCTS_DRIFTED = [
    {"id": 101, "product_name": "Wireless Headphones", "cost": 79.99, "available": True},
    {"id": 102, "product_name": "USB-C Hub", "cost": 49.99, "available": True},
    {"id": 103, "product_name": "Mechanical Keyboard", "cost": 149.99, "available": False},
]

ORDERS_STABLE = [
    {"order_id": 1001, "user_id": 1, "total_amount": 129.98, "status": "completed"},
    {"order_id": 1002, "user_id": 2, "total_amount": 49.99, "status": "pending"},
    {"order_id": 1003, "user_id": 1, "total_amount": 149.99, "status": "shipped"},
]

ORDERS_DRIFTED = [
    {"orderId": 1001, "customerId": 1, "totalPrice": 129.98, "orderStatus": "completed"},
    {"orderId": 1002, "customerId": 2, "totalPrice": 49.99, "orderStatus": "pending"},
    {"orderId": 1003, "customerId": 1, "totalPrice": 149.99, "orderStatus": "shipped"},
]


def get_mode() -> SchemaMode:
    """Get the effective mode (handles chaotic mode)."""
    global current_mode
    if current_mode == SchemaMode.CHAOTIC:
        return random.choice([SchemaMode.STABLE, SchemaMode.DRIFTED])
    return current_mode


# ============================================================================
# Admin Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Mock Legacy API",
        "version": "1.0.0",
        "current_mode": current_mode
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check."""
    return {"status": "healthy", "mode": current_mode}


@app.get("/mode", tags=["Admin"])
async def get_current_mode():
    """Get current schema mode."""
    return {"mode": current_mode}


@app.post("/mode", tags=["Admin"])
async def set_mode(mode: SchemaMode):
    """Set the schema mode."""
    global current_mode
    current_mode = mode
    return {"mode": current_mode, "message": f"Mode set to {mode}"}


# ============================================================================
# User Endpoints
# ============================================================================

@app.get("/api/users", tags=["Users"])
async def get_users():
    """Get all users."""
    mode = get_mode()
    return USERS_DRIFTED if mode == SchemaMode.DRIFTED else USERS_STABLE


@app.get("/api/users/{user_id}", tags=["Users"])
async def get_user(user_id: int):
    """Get a specific user."""
    mode = get_mode()
    users = USERS_DRIFTED if mode == SchemaMode.DRIFTED else USERS_STABLE
    
    # Find user by ID (handle both schemas)
    id_field = "uid" if mode == SchemaMode.DRIFTED else "user_id"
    for user in users:
        if user.get(id_field) == user_id:
            return user
    
    return {"error": "User not found"}, 404


@app.get("/api/user", tags=["Users"])
async def get_current_user():
    """Get the current user (simulated)."""
    mode = get_mode()
    users = USERS_DRIFTED if mode == SchemaMode.DRIFTED else USERS_STABLE
    return users[0]


@app.get("/api/profile", tags=["Users"])
async def get_profile():
    """Get user profile (alias)."""
    mode = get_mode()
    users = USERS_DRIFTED if mode == SchemaMode.DRIFTED else USERS_STABLE
    return users[0]


# ============================================================================
# Product Endpoints
# ============================================================================

@app.get("/api/products", tags=["Products"])
async def get_products():
    """Get all products."""
    mode = get_mode()
    return PRODUCTS_DRIFTED if mode == SchemaMode.DRIFTED else PRODUCTS_STABLE


@app.get("/api/products/{product_id}", tags=["Products"])
async def get_product(product_id: int):
    """Get a specific product."""
    mode = get_mode()
    products = PRODUCTS_DRIFTED if mode == SchemaMode.DRIFTED else PRODUCTS_STABLE
    
    id_field = "id" if mode == SchemaMode.DRIFTED else "product_id"
    for product in products:
        if product.get(id_field) == product_id:
            return product
    
    return {"error": "Product not found"}, 404


# ============================================================================
# Order Endpoints
# ============================================================================

@app.get("/api/orders", tags=["Orders"])
async def get_orders(user_id: Optional[int] = Query(None)):
    """Get all orders, optionally filtered by user."""
    mode = get_mode()
    orders = ORDERS_DRIFTED if mode == SchemaMode.DRIFTED else ORDERS_STABLE
    
    if user_id is not None:
        user_field = "customerId" if mode == SchemaMode.DRIFTED else "user_id"
        orders = [o for o in orders if o.get(user_field) == user_id]
    
    return orders


@app.get("/api/orders/{order_id}", tags=["Orders"])
async def get_order(order_id: int):
    """Get a specific order."""
    mode = get_mode()
    orders = ORDERS_DRIFTED if mode == SchemaMode.DRIFTED else ORDERS_STABLE
    
    id_field = "orderId" if mode == SchemaMode.DRIFTED else "order_id"
    for order in orders:
        if order.get(id_field) == order_id:
            return order
    
    return {"error": "Order not found"}, 404


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
