"""
Schema Registry - Maps endpoints to their expected Pydantic models
"""
from typing import Optional, Type
from pydantic import BaseModel
from app.models import UserProfile, Product, Order
from app.logging_config import get_logger

logger = get_logger(__name__)


class SchemaRegistry:
    """
    Registry that maps API endpoints to their expected response schemas.
    
    This allows the proxy to know what schema to validate against
    for each endpoint.
    """
    
    def __init__(self):
        self._registry: dict[str, Type[BaseModel]] = {}
        self._default_schemas()
    
    def _default_schemas(self) -> None:
        """Register default schemas for common endpoints."""
        # User endpoints
        self.register("/api/users/{id}", UserProfile)
        self.register("/api/users", UserProfile)  # For list responses
        self.register("/api/user", UserProfile)
        self.register("/api/profile", UserProfile)
        
        # Product endpoints
        self.register("/api/products/{id}", Product)
        self.register("/api/products", Product)
        self.register("/api/product", Product)
        
        # Order endpoints
        self.register("/api/orders/{id}", Order)
        self.register("/api/orders", Order)
        
        logger.info("schema_registry_initialized", count=len(self._registry))
    
    def register(self, endpoint_pattern: str, model: Type[BaseModel]) -> None:
        """
        Register a schema for an endpoint pattern.
        
        Args:
            endpoint_pattern: The endpoint pattern (can include {param})
            model: The Pydantic model class for validation
        """
        self._registry[endpoint_pattern] = model
        logger.debug(
            "schema_registered",
            endpoint=endpoint_pattern,
            model=model.__name__
        )
    
    def get_schema(self, endpoint: str) -> Optional[Type[BaseModel]]:
        """
        Get the schema for an endpoint.
        
        This supports pattern matching for path parameters.
        
        Args:
            endpoint: The actual endpoint path
            
        Returns:
            The Pydantic model class or None if not found
        """
        # Direct match first
        if endpoint in self._registry:
            return self._registry[endpoint]
        
        # Pattern matching for path parameters
        for pattern, model in self._registry.items():
            if self._matches_pattern(endpoint, pattern):
                return model
        
        return None
    
    def _matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """
        Check if an endpoint matches a pattern with path parameters.
        
        Example: "/api/users/123" matches "/api/users/{id}"
        """
        endpoint_parts = endpoint.strip("/").split("/")
        pattern_parts = pattern.strip("/").split("/")
        
        if len(endpoint_parts) != len(pattern_parts):
            return False
        
        for ep_part, pat_part in zip(endpoint_parts, pattern_parts):
            # Path parameter (e.g., {id}) matches anything
            if pat_part.startswith("{") and pat_part.endswith("}"):
                continue
            # Literal parts must match exactly
            if ep_part != pat_part:
                return False
        
        return True
    
    def list_schemas(self) -> dict[str, str]:
        """Get all registered schemas."""
        return {
            endpoint: model.__name__
            for endpoint, model in self._registry.items()
        }


# Singleton instance
schema_registry = SchemaRegistry()
