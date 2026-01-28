"""Routes package."""
from app.routes.proxy_routes import router as proxy_router
from app.routes.admin_routes import router as admin_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.chaos_routes import router as chaos_router
from app.routes.playground_routes import router as playground_router
from app.routes.mock_routes import router as mock_router

__all__ = ["proxy_router", "admin_router", "dashboard_router", "chaos_router", "playground_router", "mock_router"]

