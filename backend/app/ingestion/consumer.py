"""
Asynchronous Event Consumer Interfaces and Implementations for CAGED Ingestion Pipeline.
"""

from abc import ABC, abstractmethod
import asyncio
import time
from typing import List, Optional
from app.core.logging import get_logger
from app.ingestion.models import EngagementEvent
from app.ingestion.queue import BaseEventQueue

logger = get_logger(__name__)


class BaseEventConsumer(ABC):
    """Abstract interface for event stream consumers."""

    @abstractmethod
    async def consume_one(self, timeout: Optional[float] = None) -> Optional[EngagementEvent]:
        """Consumes a single EngagementEvent."""
        pass

    @abstractmethod
    async def consume_batch(
        self, max_batch_size: int = 100, max_wait_seconds: float = 1.0
    ) -> List[EngagementEvent]:
        """Consumes up to max_batch_size events within max_wait_seconds."""
        pass


class AsyncEventConsumer(BaseEventConsumer):
    """Internal asynchronous event consumer consuming from BaseEventQueue."""

    def __init__(self, queue: BaseEventQueue):
        self.queue = queue

    async def consume_one(self, timeout: Optional[float] = None) -> Optional[EngagementEvent]:
        """
        Retrieves a single event from the queue. Returns None if timeout expires.
        """
        try:
            event = await self.queue.get(timeout=timeout)
            return event
        except (asyncio.TimeoutError, TimeoutError):
            return None

    async def consume_batch(
        self, max_batch_size: int = 100, max_wait_seconds: float = 1.0
    ) -> List[EngagementEvent]:
        """
        Consumes a batch of up to max_batch_size events from the queue within max_wait_seconds window.
        
        Args:
            max_batch_size: Maximum number of events to pull into batch.
            max_wait_seconds: Time window limit in seconds.
            
        Returns:
            List of consumed EngagementEvent objects preserving arrival order.
        """
        batch: List[EngagementEvent] = []
        start_time = time.monotonic()
        remaining_time = max_wait_seconds

        while len(batch) < max_batch_size and remaining_time > 0:
            try:
                evt = await self.queue.get(timeout=remaining_time)
                batch.append(evt)
            except (asyncio.TimeoutError, TimeoutError):
                break
            
            elapsed = time.monotonic() - start_time
            remaining_time = max_wait_seconds - elapsed

        return batch
