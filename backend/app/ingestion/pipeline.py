"""
Continuous Stream Ingestion Pipeline & Throughput Monitoring Manager for CAGED.
"""

import asyncio
import time
from typing import Awaitable, Callable, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.ingestion.consumer import AsyncEventConsumer, BaseEventConsumer
from app.ingestion.models import EngagementEvent
from app.ingestion.producer import AsyncEventProducer, BaseEventProducer
from app.ingestion.queue import AsyncEventQueue, BackpressurePolicy, BaseEventQueue

logger = get_logger(__name__)

BatchHandlerCallback = Callable[[List[EngagementEvent]], Awaitable[None]]


class IngestionPipelineMetrics(BaseModel):
    """Real-time performance and throughput statistics for the ingestion pipeline."""

    total_produced: int = Field(default=0, description="Total events produced")
    total_consumed: int = Field(default=0, description="Total events consumed")
    total_rejected: int = Field(default=0, description="Total invalid/rejected events")
    throughput_events_per_sec: float = Field(default=0.0, description="Calculated throughput (events/sec)")
    elapsed_time_sec: float = Field(default=0.0, description="Active processing duration")
    current_queue_size: int = Field(default=0, description="Items currently in queue")


class IngestionPipeline:
    """
    Orchestrates continuous event stream ingestion, queue management, batch dispatch,
    and throughput measurement.
    """

    def __init__(
        self,
        capacity: int = 10000,
        backpressure_policy: BackpressurePolicy = BackpressurePolicy.BLOCK,
        batch_size: int = 100,
        batch_timeout_sec: float = 0.5,
    ):
        self.queue: BaseEventQueue = AsyncEventQueue(capacity=capacity, backpressure_policy=backpressure_policy)
        self.producer: BaseEventProducer = AsyncEventProducer(self.queue)
        self.consumer: BaseEventConsumer = AsyncEventConsumer(self.queue)
        
        self.batch_size = batch_size
        self.batch_timeout_sec = batch_timeout_sec
        self.handlers: List[BatchHandlerCallback] = []
        
        self.total_produced = 0
        self.total_consumed = 0
        self.total_rejected = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    def register_batch_handler(self, handler: BatchHandlerCallback) -> None:
        """Registers a callback function to receive consumed event batches."""
        self.handlers.append(handler)

    async def produce_event(self, event: EngagementEvent) -> bool:
        """Produces a single validated event into the pipeline."""
        if self.start_time is None:
            self.start_time = time.monotonic()
            
        success = await self.producer.publish(event)
        if success:
            self.total_produced += 1
        else:
            self.total_rejected += 1
        return success

    async def produce_batch(self, events: List[EngagementEvent]) -> int:
        """Produces a batch of events into the pipeline."""
        if self.start_time is None:
            self.start_time = time.monotonic()
            
        count = await self.producer.publish_batch(events)
        self.total_produced += count
        self.total_rejected += (len(events) - count)
        return count

    async def start_consumer_loop(self) -> None:
        """Starts continuous background consumer worker loop."""
        self._running = True
        if self.start_time is None:
            self.start_time = time.monotonic()
            
        self._worker_task = asyncio.create_task(self._consume_loop())

    async def _consume_loop(self) -> None:
        """Continuous internal async loop consuming batches and invoking registered handlers."""
        while self._running or not self.queue.empty():
            batch = await self.consumer.consume_batch(
                max_batch_size=self.batch_size, max_wait_seconds=self.batch_timeout_sec
            )
            if batch:
                self.total_consumed += len(batch)
                for handler in self.handlers:
                    try:
                        await handler(batch)
                    except Exception as err:
                        logger.error("Error in pipeline batch handler: %s", err, exc_info=True)
            else:
                if not self._running and self.queue.empty():
                    break
                await asyncio.sleep(0.01)

    async def stop(self) -> None:
        """Stops the consumer loop and waits for queued items to drain."""
        self._running = False
        if self._worker_task:
            await self._worker_task
        self.end_time = time.monotonic()

    def get_metrics(self) -> IngestionPipelineMetrics:
        """Calculates current pipeline throughput and performance metrics."""
        now = self.end_time or time.monotonic()
        start = self.start_time or now
        elapsed = max(0.0001, now - start)
        tps = self.total_consumed / elapsed

        return IngestionPipelineMetrics(
            total_produced=self.total_produced,
            total_consumed=self.total_consumed,
            total_rejected=self.total_rejected,
            throughput_events_per_sec=round(tps, 2),
            elapsed_time_sec=round(elapsed, 4),
            current_queue_size=self.queue.qsize(),
        )
