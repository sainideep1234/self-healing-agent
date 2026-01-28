"""
Admin API Routes - Management and debugging endpoints
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from app.database import redis_client, mongodb_client
from app.healer import schema_registry
from app.models import HealthStatus, HealingEventType
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Health check",
    description="Check the health status of all components"
)
async def health_check() -> HealthStatus:
    """Health check endpoint."""
    import httpx
    
    # Check Redis
    redis_ok = await redis_client.ping()
    
    # Check MongoDB
    mongo_ok = await mongodb_client.ping()
    
    # Check upstream
    upstream_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.legacy_api_url}/health")
            upstream_ok = response.status_code < 500
    except Exception:
        pass
    
    status = "healthy" if (redis_ok and mongo_ok) else "degraded"
    
    return HealthStatus(
        status=status,
        redis_connected=redis_ok,
        mongodb_connected=mongo_ok,
        upstream_reachable=upstream_ok
    )


@router.get(
    "/schemas",
    summary="List registered schemas",
    description="Get all registered endpoint schemas"
)
async def list_schemas() -> dict:
    """List all registered schemas."""
    return {
        "schemas": schema_registry.list_schemas(),
        "total": len(schema_registry.list_schemas())
    }


@router.get(
    "/mappings",
    summary="List cached mappings",
    description="Get all cached schema mappings from Redis"
)
async def list_mappings() -> dict:
    """List all cached mappings."""
    mappings = await redis_client.get_all_mappings()
    return {
        "mappings": [m.model_dump() for m in mappings],
        "total": len(mappings)
    }


@router.delete(
    "/mappings/{endpoint:path}",
    summary="Invalidate mapping",
    description="Invalidate a cached mapping for an endpoint"
)
async def invalidate_mapping(endpoint: str) -> dict:
    """Invalidate a specific mapping."""
    # Ensure endpoint has leading slash
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    
    deleted = await redis_client.invalidate_mapping(endpoint)
    return {
        "endpoint": endpoint,
        "deleted": deleted
    }


@router.delete(
    "/mappings",
    summary="Clear all mappings",
    description="Clear all cached schema mappings"
)
async def clear_all_mappings() -> dict:
    """Clear all cached mappings."""
    count = await redis_client.clear_all_mappings()
    return {
        "cleared": count
    }


@router.get(
    "/events",
    summary="List healing events",
    description="Query healing events from MongoDB"
)
async def list_events(
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    hours: int = Query(24, description="Look back hours"),
    limit: int = Query(100, description="Maximum events to return")
) -> dict:
    """List healing events."""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Convert event_type string to enum if provided
    type_filter = None
    if event_type:
        try:
            type_filter = HealingEventType(event_type)
        except ValueError:
            pass
    
    events = await mongodb_client.get_healing_events(
        endpoint=endpoint,
        event_type=type_filter,
        since=since,
        limit=limit
    )
    
    return {
        "events": events,
        "total": len(events),
        "filters": {
            "endpoint": endpoint,
            "event_type": event_type,
            "hours": hours
        }
    }


@router.get(
    "/stats",
    summary="Healing statistics",
    description="Get healing statistics and success rates"
)
async def healing_stats(
    hours: int = Query(24, description="Look back hours")
) -> dict:
    """Get healing statistics."""
    stats = await mongodb_client.get_healing_stats(hours=hours)
    return stats


@router.get(
    "/config",
    summary="Current configuration",
    description="Get current application configuration (redacted)"
)
async def get_config() -> dict:
    """Get current configuration (with sensitive values redacted)."""
    return {
        "server": {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug
        },
        "upstream": {
            "url": settings.legacy_api_url
        },
        "redis": {
            "url": settings.redis_url.replace(settings.redis_url.split("@")[-1] if "@" in settings.redis_url else "", "***"),
            "cache_ttl": settings.redis_cache_ttl
        },
        "healing": {
            "enabled": settings.enable_auto_healing,
            "max_attempts": settings.max_healing_attempts,
            "confidence_threshold": settings.healing_confidence_threshold,
            "llm_model": settings.llm_model
        }
    }
