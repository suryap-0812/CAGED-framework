"""
Asynchronous Event Producer Interfaces and Implementations for CAGED Ingestion Pipeline.
"""

from abc import ABC, abstractmethod
import asyncio
from typing import List, Union
from app.core.logging import get_logger
from app.ingestion.models import EngagementEvent
from app.ingestion.queue import BaseEventQueue

logger = get_logger(__name__)


class BaseEventProducer(ABC):
    """Abstract interface for event stream producers (AsyncQueue, Kafka, Redis, etc.)."""

    @abstractmethod
    async def publish(self, event: EngagementEvent) -> bool:
        """Publishes a single EngagementEvent to the stream."""
        pass

    @abstractmethod
    async def publish_batch(self, events: List[EngagementEvent]) -> int:
        """Publishes a batch of EngagementEvent objects to the stream. Returns count published."""
        pass


class AsyncEventProducer(BaseEventProducer):
    """Internal asynchronous event producer pushing to an AsyncEventQueue."""

    def __init__(self, queue: BaseEventQueue):
        self.queue = queue

    async def publish(self, event: EngagementEvent) -> bool:
        """
        Publishes a single event into the queue.
        
        Returns:
            True if published successfully, False if dropped due to backpressure.
        """
        try:
            await self.queue.put(event)
            return True
        except asyncio.QueueFull:
            logger.warning("Producer backpressure: Queue full. Event %s dropped/blocked.", event.event_id)
            return False

    async def publish_batch(self, events: List[EngagementEvent]) -> int:
        """
        Publishes a list of events sequentially.
        
        Returns:
            Number of successfully published events.
        """
        published = 0
        for evt in events:
            if await self.publish(evt):
                published += 1
        return published
