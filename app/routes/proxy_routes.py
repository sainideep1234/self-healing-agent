"""
Proxy API Routes - Handles all proxied requests
"""
from fastapi import APIRouter, Request, Response
from typing import Any

from app.proxy import proxy_service
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Proxy"])


@router.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    summary="Proxy endpoint",
    description="Proxies requests to the upstream legacy API with automatic schema healing"
)
async def proxy_endpoint(request: Request, path: str) -> Response:
    """
    Main proxy endpoint that catches all /api/* routes.
    
    This endpoint:
    1. Forwards the request to the upstream API
    2. Validates the response against expected schema
    3. Triggers healing if validation fails
    4. Returns the (possibly healed) response
    """
    # Extract request details
    method = request.method
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    
    # Remove host header (we'll set our own)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Get body for POST/PUT/PATCH
    body = None
    if method.upper() in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            body = None
    
    # Proxy the request
    result = await proxy_service.proxy_request(
        method=method,
        path=f"/api/{path}",
        headers=headers,
        body=body,
        query_params=query_params
    )
    
    # Build response headers
    response_headers = {}
    if result.get("healed"):
        response_headers["X-Schema-Healed"] = "true"
        if result.get("healing_details", {}).get("from_cache"):
            response_headers["X-Healing-Cache"] = "hit"
        else:
            response_headers["X-Healing-Cache"] = "miss"
    
    # Return response
    return Response(
        content=_serialize_body(result.get("body")),
        status_code=result.get("status_code", 200),
        media_type="application/json",
        headers=response_headers
    )


def _serialize_body(body: Any) -> bytes:
    """Serialize body to bytes for Response."""
    import json
    if body is None:
        return b""
    if isinstance(body, (dict, list)):
        return json.dumps(body, default=str).encode()
    if isinstance(body, str):
        return body.encode()
    return str(body).encode()
