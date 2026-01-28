"""
Chaos Playground Routes - API for the interactive demo frontend

This module provides endpoints for:
- SSE streaming of agent thoughts
- Chaos controls (simulate API breaks)
- Human-in-the-loop approval
- Session statistics
"""
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import httpx

from app.config import get_settings
from app.healer import agent_stream, schema_healer, ThoughtType
from app.database import redis_client
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/chaos", tags=["Chaos Playground"])


class ApprovalRequest(BaseModel):
    """Request to approve/reject a pending healing."""
    approved: bool


class HumanInLoopConfig(BaseModel):
    """Configuration for human-in-the-loop mode."""
    enabled: bool
    threshold: float = 0.7


class SimulateChangeRequest(BaseModel):
    """Request to simulate an API change."""
    change_type: str  # "rename", "type_change", "delete"
    target_field: Optional[str] = None
    new_field_name: Optional[str] = None


# ============================================================================
# SSE Streaming
# ============================================================================

@router.get(
    "/stream",
    summary="Agent Thought Stream",
    description="Server-Sent Events stream of agent thoughts in real-time"
)
async def agent_thought_stream(request: Request):
    """
    Stream agent thoughts via SSE.
    
    Connect to this endpoint to receive real-time updates
    as the agent analyzes and heals schema mismatches.
    """
    async def event_generator():
        async for event in agent_stream.subscribe():
            # Check if client disconnected
            if await request.is_disconnected():
                break
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get(
    "/history",
    summary="Get thought history",
    description="Get recent agent thought history"
)
async def get_thought_history(limit: int = Query(50, le=100)):
    """Get recent thought history."""
    return {
        "thoughts": agent_stream.get_history(limit),
        "stats": agent_stream.get_stats()
    }


@router.delete(
    "/clear",
    summary="Clear stream",
    description="Clear thought history and reset counters"
)
async def clear_stream():
    """Clear the thought stream and reset counters."""
    await agent_stream.clear()
    return {"message": "Stream cleared"}


# ============================================================================
# Human in the Loop
# ============================================================================

@router.post(
    "/approve",
    summary="Approve/Reject healing",
    description="Approve or reject a pending healing action"
)
async def approve_healing(request: ApprovalRequest):
    """Approve or reject a pending healing action."""
    result = await agent_stream.approve_pending(request.approved)
    
    if result:
        return {"message": f"Healing {'approved' if request.approved else 'rejected'}"}
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "No pending approval"}
        )


@router.post(
    "/human-in-loop",
    summary="Configure human-in-the-loop",
    description="Enable/disable human approval for low-confidence healings"
)
async def configure_human_in_loop(config: HumanInLoopConfig):
    """Configure human-in-the-loop mode."""
    schema_healer.set_approval_mode(config.enabled, config.threshold)
    
    await agent_stream.emit(
        ThoughtType.INFO,
        f"Human-in-the-loop {'enabled' if config.enabled else 'disabled'} "
        f"(threshold: {config.threshold*100:.0f}%)"
    )
    
    return {
        "enabled": config.enabled,
        "threshold": config.threshold
    }


@router.get(
    "/human-in-loop",
    summary="Get human-in-the-loop status",
    description="Get current human-in-the-loop configuration"
)
async def get_human_in_loop_status():
    """Get human-in-the-loop configuration."""
    return {
        "enabled": schema_healer._require_approval_for_low_confidence,
        "threshold": schema_healer._confidence_threshold_for_approval
    }


# ============================================================================
# Chaos Controls
# ============================================================================

# Import embedded mock API functions
from app.routes.mock_routes import set_mode as set_embedded_mode, get_mode as get_embedded_mode


def _is_embedded_mock() -> bool:
    """Check if we're using the embedded mock API."""
    legacy_url = settings.legacy_api_url.lower()
    return (
        "/mock" in legacy_url or
        legacy_url.endswith(":8000") or  # Same as gateway
        "self-healing" in legacy_url  # Points to itself on Render
    )


@router.get(
    "/mock-mode",
    summary="Get mock API mode",
    description="Get the current schema mode of the mock API"
)
async def get_mock_mode():
    """Get current mock API mode."""
    if _is_embedded_mock():
        # Use embedded mock
        return {"mode": get_embedded_mode()}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.legacy_api_url}/mode")
            return r.json()
    except Exception as e:
        # Fallback to embedded
        return {"mode": get_embedded_mode(), "fallback": True}


@router.post(
    "/break",
    summary="Break the API! 💥",
    description="Switch mock API to 'drifted' mode to simulate schema drift"
)
async def break_api():
    """
    CHAOS BUTTON: Break the API!
    
    Switches the mock API to 'drifted' mode where field names are changed.
    This will cause validation errors that the agent must heal.
    """
    try:
        # Clear cached mappings first (ignore errors if Redis unavailable)
        try:
            await redis_client.clear_all_mappings()
        except Exception as e:
            logger.warning("redis_clear_failed", error=str(e))
        
        # Always use embedded mock (simplest for production)
        set_embedded_mode("drifted")
            
        await agent_stream.emit(
            ThoughtType.ALERT,
            "💥 CHAOS BUTTON PRESSED! API schema has been broken!"
        )
        
        return {
            "message": "API BROKEN! 💥",
            "mode": "drifted",
            "changes": [
                "user_id → uid",
                "name → full_name",
                "email → email_address",
                "created_at → registered_date",
                "product_id → id",
                "title → product_name",
                "price → cost",
                "in_stock → available"
            ]
        }
    except Exception as e:
        logger.error("break_api_error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post(
    "/fix",
    summary="Fix the API 🔧",
    description="Switch mock API back to 'stable' mode"
)
async def fix_api():
    """Switch mock API back to stable mode."""
    try:
        # Clear cached mappings (ignore errors if Redis unavailable)
        try:
            await redis_client.clear_all_mappings()
        except Exception as e:
            logger.warning("redis_clear_failed", error=str(e))
        
        # Always use embedded mock
        set_embedded_mode("stable")
        
        await agent_stream.emit(
            ThoughtType.SUCCESS,
            "🔧 API restored to stable mode"
        )
        
        return {
            "message": "API fixed! 🔧",
            "mode": "stable"
        }
    except Exception as e:
        logger.error("fix_api_error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post(
    "/chaotic",
    summary="Enable chaotic mode 🎲",
    description="Switch mock API to 'chaotic' mode - randomly returns stable or drifted"
)
async def chaotic_mode():
    """Enable chaotic mode for unpredictable fun."""
    try:
        try:
            await redis_client.clear_all_mappings()
        except Exception as e:
            logger.warning("redis_clear_failed", error=str(e))
        
        # Always use embedded mock
        set_embedded_mode("chaotic")
        
        await agent_stream.emit(
            ThoughtType.ALERT,
            "🎲 CHAOTIC MODE! API will randomly change schemas!"
        )
        
        return {
            "message": "Chaos unleashed! 🎲",
            "mode": "chaotic"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ============================================================================
# Statistics
# ============================================================================

@router.get(
    "/stats",
    summary="Get chaos session stats",
    description="Get statistics for the current chaos session"
)
async def get_session_stats():
    """Get chaos session statistics."""
    stream_stats = agent_stream.get_stats()
    
    return {
        "stream": stream_stats,
        "cost": {
            "total_usd": stream_stats["total_cost_usd"],
            "formatted": f"${stream_stats['total_cost_usd']:.4f}"
        },
        "healings": {
            "count": stream_stats["session_healings"],
            "average_cost": round(
                stream_stats["total_cost_usd"] / max(1, stream_stats["session_healings"]),
                6
            )
        }
    }
