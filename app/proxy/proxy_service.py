"""
Proxy Service - The core proxy that forwards requests to upstream API
and handles schema healing when validation fails.
"""
import time
from typing import Any, Optional
import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.logging_config import get_logger
from app.models import (
    HealingEvent,
    HealingEventType,
    SchemaMapping,
)
from app.database import redis_client, mongodb_client
from app.healer import schema_healer, schema_registry

logger = get_logger(__name__)


class ProxyService:
    """
    Intelligent proxy service that:
    1. Forwards requests to the legacy upstream API
    2. Validates responses against expected schemas
    3. Triggers the healing agent when validation fails
    4. Applies cached mappings for transformed responses
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True
            )
        return self._http_client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def proxy_request(
        self,
        method: str,
        path: str,
        headers: Optional[dict[str, str]] = None,
        body: Optional[dict[str, Any]] = None,
        query_params: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        Proxy a request to the upstream API with healing support.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: The request path
            headers: Optional request headers
            body: Optional request body (for POST/PUT)
            query_params: Optional query parameters
            
        Returns:
            Dictionary containing response data and healing info
        """
        start_time = time.time()
        normalized_path = path if path.startswith("/") else f"/{path}"
        upstream_url = f"{self.settings.legacy_api_url}{normalized_path}"
        
        logger.info(
            "proxy_request_start",
            method=method,
            path=normalized_path,
            upstream_url=upstream_url
        )
        
        client = await self.get_client()
        
        # Prepare request kwargs
        request_kwargs = {
            "method": method,
            "url": upstream_url,
            "headers": headers or {},
            "params": query_params or {}
        }
        
        if body and method.upper() in ["POST", "PUT", "PATCH"]:
            request_kwargs["json"] = body
        
        try:
            # Make upstream request
            response = await client.request(**request_kwargs)
            
            logger.debug(
                "upstream_response",
                status_code=response.status_code,
                path=normalized_path
            )
            
            # Handle non-success responses
            if response.status_code >= 400:
                await mongodb_client.log_healing_event(HealingEvent(
                    event_type=HealingEventType.HTTP_ERROR,
                    endpoint=normalized_path,
                    original_error=f"HTTP {response.status_code}",
                    metadata={
                        "status_code": response.status_code,
                        "response_text": response.text[:500]
                    }
                ))
                
                return {
                    "status_code": response.status_code,
                    "body": {"error": response.text},
                    "healed": False,
                    "headers": dict(response.headers)
                }
            
            # Parse response
            try:
                response_data = response.json()
            except Exception:
                # Return raw text if not JSON
                return {
                    "status_code": response.status_code,
                    "body": response.text,
                    "healed": False,
                    "headers": dict(response.headers)
                }
            
            # Handle list responses - validate first item
            is_list = isinstance(response_data, list)
            data_to_validate = response_data[0] if is_list and response_data else response_data
            
            # Get expected schema
            expected_model = schema_registry.get_schema(normalized_path)
            
            if not expected_model:
                logger.debug("no_schema_registered", path=normalized_path)
                return {
                    "status_code": response.status_code,
                    "body": response_data,
                    "healed": False,
                    "headers": dict(response.headers)
                }
            
            # Check for cached mapping first
            cached_mapping = await redis_client.get_mapping(normalized_path)
            
            if cached_mapping:
                # Apply cached mapping
                if is_list:
                    healed_data = [
                        schema_healer.apply_mapping(item, cached_mapping)
                        for item in response_data
                    ]
                else:
                    healed_data = schema_healer.apply_mapping(response_data, cached_mapping)
                
                logger.info(
                    "applied_cached_mapping",
                    path=normalized_path,
                    version=cached_mapping.version
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                return {
                    "status_code": response.status_code,
                    "body": healed_data,
                    "healed": True,
                    "healing_details": {
                        "from_cache": True,
                        "mapping_version": cached_mapping.version,
                        "duration_ms": round(duration_ms, 2)
                    },
                    "headers": dict(response.headers)
                }
            
            # Try to validate against expected schema
            try:
                if is_list:
                    for item in response_data:
                        expected_model.model_validate(item)
                else:
                    expected_model.model_validate(response_data)
                
                # Validation passed - no healing needed
                logger.debug("schema_validation_passed", path=normalized_path)
                
                return {
                    "status_code": response.status_code,
                    "body": response_data,
                    "healed": False,
                    "headers": dict(response.headers)
                }
                
            except ValidationError as e:
                # Schema mismatch detected!
                logger.warning(
                    "schema_validation_failed",
                    path=normalized_path,
                    errors=len(e.errors())
                )
                
                # Log the mismatch event
                await mongodb_client.log_healing_event(HealingEvent(
                    event_type=HealingEventType.SCHEMA_MISMATCH,
                    endpoint=normalized_path,
                    original_error=str(e),
                    original_response=data_to_validate,
                    metadata={"expected_model": expected_model.__name__}
                ))
                
                # Check if auto-healing is enabled
                if not self.settings.enable_auto_healing:
                    logger.info("auto_healing_disabled", path=normalized_path)
                    return {
                        "status_code": 500,
                        "body": {
                            "error": "Schema validation failed",
                            "details": str(e),
                            "healing_disabled": True
                        },
                        "healed": False,
                        "headers": dict(response.headers)
                    }
                
                # Trigger the healing agent
                new_mapping = await schema_healer.analyze_and_heal(
                    endpoint=normalized_path,
                    expected_model=expected_model,
                    actual_response=data_to_validate,
                    validation_error=e
                )
                
                if new_mapping:
                    # Apply the new mapping
                    if is_list:
                        healed_data = [
                            schema_healer.apply_mapping(item, new_mapping)
                            for item in response_data
                        ]
                    else:
                        healed_data = schema_healer.apply_mapping(response_data, new_mapping)
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    logger.info(
                        "healing_applied",
                        path=normalized_path,
                        duration_ms=round(duration_ms, 2)
                    )
                    
                    return {
                        "status_code": response.status_code,
                        "body": healed_data,
                        "healed": True,
                        "healing_details": {
                            "from_cache": False,
                            "mapping_version": new_mapping.version,
                            "field_mappings": [
                                {
                                    "source": m.source_field,
                                    "target": m.target_field,
                                    "confidence": m.confidence
                                }
                                for m in new_mapping.field_mappings
                            ],
                            "duration_ms": round(duration_ms, 2)
                        },
                        "headers": dict(response.headers)
                    }
                else:
                    # Healing failed
                    return {
                        "status_code": 500,
                        "body": {
                            "error": "Schema healing failed",
                            "original_response": response_data,
                            "validation_error": str(e)
                        },
                        "healed": False,
                        "headers": dict(response.headers)
                    }
                    
        except httpx.RequestError as e:
            logger.error(
                "upstream_request_failed",
                path=normalized_path,
                error=str(e)
            )
            
            return {
                "status_code": 502,
                "body": {"error": f"Upstream request failed: {str(e)}"},
                "healed": False,
                "headers": {}
            }
        except Exception as e:
            logger.error(
                "proxy_error",
                path=normalized_path,
                error=str(e)
            )
            
            return {
                "status_code": 500,
                "body": {"error": f"Proxy error: {str(e)}"},
                "healed": False,
                "headers": {}
            }


# Singleton instance
proxy_service = ProxyService()
