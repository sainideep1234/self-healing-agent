"""
Agent Stream - Real-time streaming of agent thoughts via SSE

This module enables the "Glass Box" experience where users can see
the agent's internal monologue as it analyzes and fixes schema drift.
"""
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque

from app.logging_config import get_logger

logger = get_logger(__name__)


class ThoughtType(str, Enum):
    """Types of agent thoughts for visualization."""
    ALERT = "alert"           # 🔴 Error detected
    ANALYZING = "analyzing"   # 🧐 Analyzing the problem
    SCANNING = "scanning"     # 🔍 Scanning available data
    HYPOTHESIS = "hypothesis" # 💡 Forming a hypothesis
    PATCHING = "patching"     # 🛠️ Applying a fix
    RETRYING = "retrying"     # 🔄 Retrying the request
    SUCCESS = "success"       # 🟢 Success
    FAILURE = "failure"       # ❌ Failed
    WAITING = "waiting"       # ⏸️ Waiting for approval
    INFO = "info"             # ℹ️ General info


@dataclass
class AgentThought:
    """Represents a single agent thought/step."""
    id: str
    type: ThoughtType
    message: str
    timestamp: str
    details: Optional[dict] = None
    confidence: Optional[float] = None
    cost_usd: Optional[float] = None
    requires_approval: bool = False


class AgentStreamManager:
    """
    Manages real-time streaming of agent thoughts to connected clients.
    Uses Server-Sent Events (SSE) for push notifications.
    """
    
    def __init__(self, max_history: int = 100):
        self._subscribers: list[asyncio.Queue] = []
        self._thought_history: deque = deque(maxlen=max_history)
        self._thought_counter = 0
        self._pending_approval: Optional[AgentThought] = None
        self._approval_event: Optional[asyncio.Event] = None
        self._approval_result: bool = False
        
        # Cost tracking
        self._total_cost_usd = 0.0
        self._session_healing_count = 0
    
    def _generate_id(self) -> str:
        """Generate unique thought ID."""
        self._thought_counter += 1
        return f"thought_{self._thought_counter}"
    
    async def emit(
        self,
        thought_type: ThoughtType,
        message: str,
        details: Optional[dict] = None,
        confidence: Optional[float] = None,
        cost_usd: Optional[float] = None,
        requires_approval: bool = False
    ) -> AgentThought:
        """
        Emit a new agent thought to all subscribers.
        
        Args:
            thought_type: Type of thought for styling
            message: The thought message
            details: Optional additional data
            confidence: Optional confidence score (0-1)
            cost_usd: Optional cost in USD
            requires_approval: If True, blocks until user approves
            
        Returns:
            The created AgentThought
        """
        thought = AgentThought(
            id=self._generate_id(),
            type=thought_type,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            details=details,
            confidence=confidence,
            cost_usd=cost_usd,
            requires_approval=requires_approval
        )
        
        # Track cost
        if cost_usd:
            self._total_cost_usd += cost_usd
        
        # Store in history
        self._thought_history.append(thought)
        
        # Broadcast to all subscribers
        event_data = json.dumps(asdict(thought), default=str)
        
        for queue in self._subscribers:
            try:
                await queue.put(event_data)
            except Exception as e:
                logger.error("stream_emit_error", error=str(e))
        
        logger.debug(
            "thought_emitted",
            type=thought_type.value,
            message=message[:50]
        )
        
        # Handle approval workflow
        if requires_approval:
            self._pending_approval = thought
            self._approval_event = asyncio.Event()
            
            # Wait for approval (with timeout)
            try:
                await asyncio.wait_for(
                    self._approval_event.wait(),
                    timeout=60.0  # 1 minute timeout
                )
                return self._approval_result
            except asyncio.TimeoutError:
                await self.emit(
                    ThoughtType.FAILURE,
                    "Approval timeout - proceeding with caution"
                )
                return True  # Default to proceed
        
        return thought
    
    async def approve_pending(self, approved: bool) -> bool:
        """
        Approve or reject a pending healing action.
        
        Args:
            approved: Whether the user approves
            
        Returns:
            True if there was a pending approval
        """
        if self._approval_event and self._pending_approval:
            self._approval_result = approved
            self._approval_event.set()
            
            status = "approved" if approved else "rejected"
            await self.emit(
                ThoughtType.INFO,
                f"User {status} the healing action"
            )
            
            self._pending_approval = None
            self._approval_event = None
            return True
        
        return False
    
    async def subscribe(self) -> AsyncGenerator[str, None]:
        """
        Subscribe to the thought stream.
        Yields SSE-formatted events.
        """
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        
        logger.info("stream_subscriber_added", count=len(self._subscribers))
        
        try:
            # Send connection confirmation
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Agent stream connected'})}\n\n"
            
            # Send recent history
            for thought in list(self._thought_history)[-10:]:
                yield f"data: {json.dumps(asdict(thought), default=str)}\n\n"
            
            # Stream new thoughts
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    
        except asyncio.CancelledError:
            pass
        finally:
            self._subscribers.remove(queue)
            logger.info("stream_subscriber_removed", count=len(self._subscribers))
    
    def get_stats(self) -> dict:
        """Get streaming statistics."""
        return {
            "subscribers": len(self._subscribers),
            "total_thoughts": self._thought_counter,
            "total_cost_usd": round(self._total_cost_usd, 6),
            "session_healings": self._session_healing_count,
            "pending_approval": self._pending_approval is not None
        }
    
    def increment_healing_count(self):
        """Increment the healing counter."""
        self._session_healing_count += 1
    
    def get_history(self, limit: int = 50) -> list[dict]:
        """Get recent thought history."""
        return [asdict(t) for t in list(self._thought_history)[-limit:]]
    
    async def clear(self):
        """Clear history and reset counters."""
        self._thought_history.clear()
        self._thought_counter = 0
        self._total_cost_usd = 0.0
        self._session_healing_count = 0
        
        await self.emit(ThoughtType.INFO, "Agent stream cleared")


# Singleton instance
agent_stream = AgentStreamManager()
