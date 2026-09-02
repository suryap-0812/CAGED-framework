"""
Asynchronous Stream Event Queue and Backpressure Control for CAGED.
"""

from abc import ABC, abstractmethod
import asyncio
from enum import Enum
from typing import Optional
from app.core.exceptions import CAGEDException
from app.ingestion.models import EngagementEvent


class BackpressurePolicy(str, Enum):
    """Backpressure handling strategy when queue reaches maximum capacity."""

    BLOCK = "block"            # Asynchronously block producer until space opens
    DROP_OLDEST = "drop_oldest"  # Evict oldest event to accommodate new event
    RAISE_ERROR = "raise_error"  # Immediately raise BackpressureException


class BackpressureException(CAGEDException):
    """Raised when queue is full under RAISE_ERROR backpressure policy."""

    def __init__(self, message: str = "Stream buffer queue capacity exceeded"):
        super().__init__(message=message, status_code=503)


class BaseEventQueue(ABC):
    """Abstract interface for event stream queues."""

    @abstractmethod
    async def put(self, event: EngagementEvent) -> None:
        """Puts an event onto the queue."""
        pass

    @abstractmethod
    async def get(self, timeout: Optional[float] = None) -> EngagementEvent:
        """Retrieves an event from the queue."""
        pass

    @abstractmethod
    def qsize(self) -> int:
        """Returns the current number of events in queue."""
        pass

    @abstractmethod
    def empty(self) -> bool:
        """Returns True if queue is empty."""
        pass

    @abstractmethod
    def full(self) -> bool:
        """Returns True if queue has reached capacity."""
        pass


class AsyncEventQueue(BaseEventQueue):
    """
    In-memory asyncio queue with configurable capacity and backpressure policy.
    """

    def __init__(
        self,
        capacity: int = 10000,
        backpressure_policy: BackpressurePolicy = BackpressurePolicy.BLOCK,
    ):
        self.capacity = capacity
        self.policy = backpressure_policy
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=capacity)
        self.dropped_events_count: int = 0

    async def put(self, event: EngagementEvent) -> None:
        """Puts an event into the queue according to configured backpressure policy."""
        if self._queue.full():
            if self.policy == BackpressurePolicy.BLOCK:
                await self._queue.put(event)
            elif self.policy == BackpressurePolicy.DROP_OLDEST:
                try:
                    _ = self._queue.get_nowait()
                    self._queue.task_done()
                    self.dropped_events_count += 1
                except asyncio.QueueEmpty:
                    pass
                await self._queue.put(event)
            elif self.policy == BackpressurePolicy.RAISE_ERROR:
                raise BackpressureException(f"Buffer full ({self.capacity} events). Cannot enqueue event {event.event_id}.")
        else:
            await self._queue.put(event)

    async def get(self, timeout: Optional[float] = None) -> EngagementEvent:
        """Gets the next event from the queue, optionally waiting up to timeout seconds."""
        if timeout is None:
            return await self._queue.get()
        return await asyncio.wait_for(self._queue.get(), timeout=timeout)

    def task_done(self) -> None:
        """Signals that a formerly enqueued task is complete."""
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()

    def full(self) -> bool:
        return self._queue.full()
