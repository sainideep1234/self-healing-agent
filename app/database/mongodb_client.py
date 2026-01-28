"""
MongoDB Client for storing healing events and analytics
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime, timedelta
from app.config import get_settings
from app.logging_config import get_logger
from app.models import HealingEvent, HealingEventType

logger = get_logger(__name__)


class MongoDBClient:
    """Async MongoDB client for healing event storage and analytics."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self._client = AsyncIOMotorClient(self.settings.mongodb_url)
            self._db = self._client[self.settings.mongodb_db_name]
            
            # Test connection
            await self._client.admin.command('ping')
            logger.info(
                "mongodb_connected", 
                url=self.settings.mongodb_url,
                database=self.settings.mongodb_db_name
            )
            
            # Create indexes
            await self._create_indexes()
        except Exception as e:
            logger.error("mongodb_connection_failed", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            self._client.close()
            logger.info("mongodb_disconnected")
    
    async def ping(self) -> bool:
        """Check if MongoDB is responsive."""
        try:
            if self._client is not None:
                await self._client.admin.command('ping')
                return True
        except Exception:
            pass
        return False
    
    async def _create_indexes(self) -> None:
        """Create necessary indexes for performance."""
        if self._db is None:
            return
        
        try:
            # Healing events collection
            events = self._db.healing_events
            await events.create_index("endpoint")
            await events.create_index("event_type")
            await events.create_index("timestamp")
            await events.create_index([("endpoint", 1), ("timestamp", -1)])
            
            logger.debug("mongodb_indexes_created")
        except Exception as e:
            logger.error("mongodb_index_error", error=str(e))
    
    async def log_healing_event(self, event: HealingEvent) -> str:
        """
        Log a healing event to MongoDB.
        
        Args:
            event: The healing event to log
            
        Returns:
            The inserted document ID as string
        """
        if self._db is None:
            logger.warning("mongodb_not_connected")
            return ""
        
        try:
            collection = self._db.healing_events
            doc = event.model_dump()
            
            # Convert datetime to MongoDB format
            if "timestamp" in doc and isinstance(doc["timestamp"], datetime):
                doc["timestamp"] = doc["timestamp"]
            
            # Handle nested datetimes in applied_mapping
            if doc.get("applied_mapping") and doc["applied_mapping"].get("created_at"):
                if isinstance(doc["applied_mapping"]["created_at"], datetime):
                    doc["applied_mapping"]["created_at"] = doc["applied_mapping"]["created_at"]
            
            result = await collection.insert_one(doc)
            event_id = str(result.inserted_id)
            
            logger.info(
                "healing_event_logged",
                event_id=event_id,
                event_type=event.event_type.value,
                endpoint=event.endpoint
            )
            return event_id
        except Exception as e:
            logger.error("healing_event_log_error", error=str(e))
            return ""
    
    async def get_healing_events(
        self,
        endpoint: Optional[str] = None,
        event_type: Optional[HealingEventType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Query healing events with optional filters.
        
        Args:
            endpoint: Filter by endpoint
            event_type: Filter by event type
            since: Filter events after this timestamp
            limit: Maximum number of events to return
            
        Returns:
            List of healing event documents
        """
        if self._db is None:
            return []
        
        try:
            collection = self._db.healing_events
            
            # Build query
            query = {}
            if endpoint:
                query["endpoint"] = endpoint
            if event_type:
                query["event_type"] = event_type.value
            if since:
                query["timestamp"] = {"$gte": since}
            
            cursor = collection.find(query).sort("timestamp", -1).limit(limit)
            events = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for event in events:
                event["_id"] = str(event["_id"])
            
            return events
        except Exception as e:
            logger.error("healing_events_query_error", error=str(e))
            return []
    
    async def get_healing_stats(self, hours: int = 24) -> dict:
        """
        Get healing statistics for the past N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary containing healing statistics
        """
        if self._db is None:
            return {}
        
        try:
            collection = self._db.healing_events
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Aggregation pipeline
            pipeline = [
                {"$match": {"timestamp": {"$gte": since}}},
                {"$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1}
                }}
            ]
            
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=100)
            
            stats = {
                "period_hours": hours,
                "total_events": 0,
                "by_type": {}
            }
            
            for result in results:
                event_type = result["_id"]
                count = result["count"]
                stats["by_type"][event_type] = count
                stats["total_events"] += count
            
            # Calculate success rate
            success_count = stats["by_type"].get(HealingEventType.HEALING_SUCCESS.value, 0)
            started_count = stats["by_type"].get(HealingEventType.HEALING_STARTED.value, 0)
            
            if started_count > 0:
                stats["success_rate"] = round(success_count / started_count * 100, 2)
            else:
                stats["success_rate"] = 0.0
            
            return stats
        except Exception as e:
            logger.error("healing_stats_error", error=str(e))
            return {}


# Singleton instance
mongodb_client = MongoDBClient()
