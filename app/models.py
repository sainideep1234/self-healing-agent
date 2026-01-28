"""
Pydantic Models for the Self-Healing API Gateway
"""
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from enum import Enum


# ============================================================================
# Expected Schema Models (What the CLIENT expects)
# ============================================================================

class UserProfile(BaseModel):
    """Expected user profile schema from the legacy API."""
    user_id: int = Field(..., description="User's unique identifier")
    name: str = Field(..., description="User's full name")
    email: Optional[str] = Field(None, description="User's email address")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")


class Product(BaseModel):
    """Expected product schema from the legacy API."""
    product_id: int = Field(..., description="Product's unique identifier")
    title: str = Field(..., description="Product title")
    price: float = Field(..., description="Product price")
    in_stock: bool = Field(True, description="Whether product is in stock")


class Order(BaseModel):
    """Expected order schema from the legacy API."""
    order_id: int = Field(..., description="Order's unique identifier")
    user_id: int = Field(..., description="User who placed the order")
    total_amount: float = Field(..., description="Total order amount")
    status: str = Field(..., description="Order status")


# ============================================================================
# Schema Mapping Models
# ============================================================================

class FieldMapping(BaseModel):
    """Represents a field mapping from old to new schema."""
    source_field: str = Field(..., description="Field name in the upstream response")
    target_field: str = Field(..., description="Field name expected by client")
    transform: Optional[str] = Field(None, description="Optional transformation function name")
    confidence: float = Field(1.0, description="Confidence score of the mapping")


class SchemaMapping(BaseModel):
    """Complete schema mapping for an endpoint."""
    endpoint: str = Field(..., description="The API endpoint path")
    version: int = Field(1, description="Mapping version number")
    field_mappings: list[FieldMapping] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field("auto", description="Who created this mapping (auto/manual)")
    llm_model: Optional[str] = Field(None, description="LLM model used for auto-healing")


# ============================================================================
# Healing Event Models
# ============================================================================

class HealingEventType(str, Enum):
    """Types of healing events."""
    SCHEMA_MISMATCH = "schema_mismatch"
    HTTP_ERROR = "http_error"
    VALIDATION_ERROR = "validation_error"
    HEALING_STARTED = "healing_started"
    HEALING_SUCCESS = "healing_success"
    HEALING_FAILED = "healing_failed"


class HealingEvent(BaseModel):
    """Record of a healing event for analytics."""
    event_id: Optional[str] = Field(None, description="Unique event ID")
    event_type: HealingEventType
    endpoint: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    original_error: Optional[str] = Field(None)
    original_response: Optional[dict[str, Any]] = Field(None)
    applied_mapping: Optional[SchemaMapping] = Field(None)
    success: bool = Field(False)
    duration_ms: Optional[float] = Field(None)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# API Request/Response Models
# ============================================================================

class ProxyRequest(BaseModel):
    """Request to be proxied to the upstream API."""
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Request path")
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[dict[str, Any]] = Field(None)
    query_params: dict[str, str] = Field(default_factory=dict)


class ProxyResponse(BaseModel):
    """Response from the proxy."""
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = Field(None)
    healed: bool = Field(False, description="Whether the response was healed")
    healing_details: Optional[dict[str, Any]] = Field(None)


class HealthStatus(BaseModel):
    """Health check response."""
    status: str = Field("healthy")
    redis_connected: bool = Field(False)
    mongodb_connected: bool = Field(False)
    upstream_reachable: bool = Field(False)
    version: str = Field("1.0.0")
