"""
Self-Healing API Gateway - Main Application

This is the entry point for the FastAPI application that provides
intelligent schema healing for upstream API changes.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import setup_logging, get_logger
from app.database import redis_client, mongodb_client
from app.proxy import proxy_service
from app.routes import proxy_router, admin_router, dashboard_router, chaos_router, playground_router

# Initialize settings and logging
settings = get_settings()
setup_logging(settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Manages startup and shutdown of database connections.
    """
    # Startup
    logger.info(
        "application_starting",
        host=settings.host,
        port=settings.port,
        upstream=settings.legacy_api_url
    )
    
    try:
        await redis_client.connect()
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
    
    try:
        await mongodb_client.connect()
    except Exception as e:
        logger.error("mongodb_connection_failed", error=str(e))
    
    logger.info("application_started")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("application_stopping")
    
    await proxy_service.close()
    await redis_client.disconnect()
    await mongodb_client.disconnect()
    
    logger.info("application_stopped")


# Create FastAPI application
app = FastAPI(
    title="Self-Healing API Gateway",
    description="""
# 🔧 Self-Healing API Gateway

An intelligent proxy that automatically adapts to upstream API schema changes using LLM-powered healing.

## Features

- **Real-Time Schema Detection**: Automatically detects when upstream API responses don't match expected schemas
- **LLM-Powered Healing**: Uses AI to analyze schema mismatches and generate field mappings
- **Intelligent Caching**: Stores healing rules in Redis for instant subsequent requests
- **Full Observability**: Logs all healing events to MongoDB for analytics

## How It Works

1. Client makes request → Proxy forwards to upstream API
2. Proxy validates response against expected Pydantic schema
3. If validation fails → LLM agent analyzes the mismatch
4. Agent generates field mappings → Cached in Redis
5. Healed response returned to client

## API Endpoints

- `/api/*` - Proxied endpoints (automatically healed)
- `/admin/*` - Management and debugging endpoints
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(proxy_router)
app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(chaos_router)
app.include_router(playground_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with gateway info."""
    return {
        "name": "Self-Healing API Gateway",
        "version": "1.0.0",
        "status": "running",
        "playground": "/playground",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "admin": "/admin/health",
        "chaos_api": "/chaos"
    }

