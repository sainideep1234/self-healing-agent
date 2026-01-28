"""
Embedded Mock API Routes - For production deployment without separate mock service

This provides mock user/product endpoints directly in the main app,
simulating a "legacy API" that can have its schema changed dynamically.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
import random

router = APIRouter(prefix="/mock", tags=["Mock API (Embedded)"])

# Global state for mock API mode
_mock_mode = "stable"


# ============================================================================
# Mock Data
# ============================================================================

USERS_STABLE = [
    {"user_id": 1, "name": "Alice Johnson", "email": "alice@example.com", "created_at": "2024-01-15T10:30:00Z"},
    {"user_id": 2, "name": "Bob Smith", "email": "bob@example.com", "created_at": "2024-02-20T14:45:00Z"},
    {"user_id": 3, "name": "Charlie Brown", "email": "charlie@example.com", "created_at": "2024-03-10T09:00:00Z"},
]

USERS_DRIFTED = [
    {"uid": 1, "full_name": "Alice Johnson", "email_address": "alice@example.com", "registered_date": "2024-01-15"},
    {"uid": 2, "full_name": "Bob Smith", "email_address": "bob@example.com", "registered_date": "2024-02-20"},
    {"uid": 3, "full_name": "Charlie Brown", "email_address": "charlie@example.com", "registered_date": "2024-03-10"},
]

PRODUCTS_STABLE = [
    {"product_id": 101, "title": "Wireless Mouse", "price": 29.99, "in_stock": True},
    {"product_id": 102, "title": "Mechanical Keyboard", "price": 89.99, "in_stock": True},
    {"product_id": 103, "title": "USB-C Hub", "price": 49.99, "in_stock": False},
]

PRODUCTS_DRIFTED = [
    {"id": 101, "product_name": "Wireless Mouse", "cost": 29.99, "available": True},
    {"id": 102, "product_name": "Mechanical Keyboard", "cost": 89.99, "available": True},
    {"id": 103, "product_name": "USB-C Hub", "cost": 49.99, "available": False},
]


def get_mode() -> str:
    """Get current mock mode."""
    global _mock_mode
    if _mock_mode == "chaotic":
        return random.choice(["stable", "drifted"])
    return _mock_mode


def set_mode(mode: str):
    """Set mock mode."""
    global _mock_mode
    _mock_mode = mode


# ============================================================================
# Mode Endpoint
# ============================================================================

@router.get("/mode")
async def get_mock_mode():
    """Get the current mock API mode."""
    return {"mode": _mock_mode}


@router.post("/mode")
async def set_mock_mode(mode: str = Query(..., description="stable, drifted, or chaotic")):
    """Set the mock API mode."""
    if mode not in ["stable", "drifted", "chaotic"]:
        return {"error": "Invalid mode. Use: stable, drifted, chaotic"}
    
    set_mode(mode)
    return {"mode": mode, "message": f"Mode changed to {mode}"}


# ============================================================================
# User Endpoints
# ============================================================================

@router.get("/api/users")
async def get_all_users():
    """Get all users."""
    mode = get_mode()
    if mode == "drifted":
        return USERS_DRIFTED
    return USERS_STABLE


@router.get("/api/users/{user_id}")
async def get_user(user_id: int):
    """Get a specific user by ID."""
    mode = get_mode()
    
    if mode == "drifted":
        users = USERS_DRIFTED
        user = next((u for u in users if u["uid"] == user_id), None)
    else:
        users = USERS_STABLE
        user = next((u for u in users if u["user_id"] == user_id), None)
    
    if not user:
        # Return first user as fallback for demo
        user = users[0] if users else {}
    
    return user


# ============================================================================
# Product Endpoints
# ============================================================================

@router.get("/api/products")
async def get_all_products():
    """Get all products."""
    mode = get_mode()
    if mode == "drifted":
        return PRODUCTS_DRIFTED
    return PRODUCTS_STABLE


@router.get("/api/products/{product_id}")
async def get_product(product_id: int):
    """Get a specific product by ID."""
    mode = get_mode()
    
    if mode == "drifted":
        products = PRODUCTS_DRIFTED
        product = next((p for p in products if p["id"] == product_id), None)
    else:
        products = PRODUCTS_STABLE
        product = next((p for p in products if p["product_id"] == product_id), None)
    
    if not product:
        product = products[0] if products else {}
    
    return product


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def mock_health():
    """Health check for embedded mock API."""
    return {
        "status": "healthy",
        "mode": _mock_mode,
        "service": "embedded-mock-api"
    }
