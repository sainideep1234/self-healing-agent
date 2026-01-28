"""
Redis Client for caching schema mappings
"""
import redis.asyncio as redis
import json
from typing import Optional
from app.config import get_settings
from app.logging_config import get_logger
from app.models import SchemaMapping

logger = get_logger(__name__)


class RedisClient:
    """Async Redis client for caching healing rules."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[redis.Redis] = None
        self._prefix = "schema_healer:"
    
    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._client.ping()
            logger.info("redis_connected", url=self.settings.redis_url)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            logger.info("redis_disconnected")
    
    async def ping(self) -> bool:
        """Check if Redis is responsive."""
        try:
            if self._client is not None:
                await self._client.ping()
                return True
        except Exception:
            pass
        return False
    
    def _make_key(self, endpoint: str) -> str:
        """Generate Redis key for an endpoint mapping."""
        return f"{self._prefix}mapping:{endpoint}"
    
    async def get_mapping(self, endpoint: str) -> Optional[SchemaMapping]:
        """
        Retrieve cached schema mapping for an endpoint.
        
        Args:
            endpoint: The API endpoint path
            
        Returns:
            SchemaMapping if found, None otherwise
        """
        if self._client is None:
            logger.warning("redis_not_connected")
            return None
        
        key = self._make_key(endpoint)
        try:
            data = await self._client.get(key)
            if data:
                mapping = SchemaMapping.model_validate_json(data)
                logger.debug("cache_hit", endpoint=endpoint, version=mapping.version)
                return mapping
            logger.debug("cache_miss", endpoint=endpoint)
            return None
        except Exception as e:
            logger.error("cache_get_error", endpoint=endpoint, error=str(e))
            return None
    
    async def set_mapping(
        self, 
        endpoint: str, 
        mapping: SchemaMapping,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache a schema mapping for an endpoint.
        
        Args:
            endpoint: The API endpoint path
            mapping: The schema mapping to cache
            ttl: Optional TTL in seconds (defaults to config)
            
        Returns:
            True if successful, False otherwise
        """
        if self._client is None:
            logger.warning("redis_not_connected")
            return False
        
        key = self._make_key(endpoint)
        ttl = ttl or self.settings.redis_cache_ttl
        
        try:
            await self._client.setex(
                key,
                ttl,
                mapping.model_dump_json()
            )
            logger.info(
                "cache_set", 
                endpoint=endpoint, 
                version=mapping.version,
                ttl=ttl
            )
            return True
        except Exception as e:
            logger.error("cache_set_error", endpoint=endpoint, error=str(e))
            return False
    
    async def invalidate_mapping(self, endpoint: str) -> bool:
        """
        Invalidate (delete) a cached mapping.
        
        Args:
            endpoint: The API endpoint path
            
        Returns:
            True if deleted, False otherwise
        """
        if self._client is None:
            return False
        
        key = self._make_key(endpoint)
        try:
            result = await self._client.delete(key)
            logger.info("cache_invalidated", endpoint=endpoint, deleted=result > 0)
            return result > 0
        except Exception as e:
            logger.error("cache_invalidate_error", endpoint=endpoint, error=str(e))
            return False
    
    async def get_all_mappings(self) -> list[SchemaMapping]:
        """Get all cached mappings."""
        if self._client is None:
            return []
        
        try:
            pattern = f"{self._prefix}mapping:*"
            keys = await self._client.keys(pattern)
            mappings = []
            for key in keys:
                data = await self._client.get(key)
                if data:
                    mappings.append(SchemaMapping.model_validate_json(data))
            return mappings
        except Exception as e:
            logger.error("cache_get_all_error", error=str(e))
            return []
    
    async def clear_all_mappings(self) -> int:
        """Clear all cached mappings. Returns count of deleted keys."""
        if self._client is None:
            return 0
        
        try:
            pattern = f"{self._prefix}mapping:*"
            keys = await self._client.keys(pattern)
            if keys:
                deleted = await self._client.delete(*keys)
                logger.info("cache_cleared", count=deleted)
                return deleted
            return 0
        except Exception as e:
            logger.error("cache_clear_error", error=str(e))
            return 0


# Singleton instance
redis_client = RedisClient()
