"""
Unit and Integration Tests for Event Stream Ingestion & Pipeline.
"""

from datetime import datetime, timezone
import pytest

from app.ingestion.models import EngagementEvent, MetricType
from app.ingestion.producer import AsyncEventProducer
from app.ingestion.consumer import AsyncEventConsumer
from app.ingestion.queue import AsyncEventQueue, BackpressurePolicy, BackpressureException
from app.ingestion.pipeline import IngestionPipeline
from app.simulation.event_generator import EventGenerator, EventGeneratorConfig
from app.preprocessing.privacy import pseudonymize_user_id


@pytest.mark.asyncio
async def test_queue_single_and_batch_put_get():
    """Tests basic put and get operations on AsyncEventQueue."""
    queue = AsyncEventQueue(capacity=10)
    producer = AsyncEventProducer(queue)
    consumer = AsyncEventConsumer(queue)

    evt = EngagementEvent(
        event_id="evt_test_1",
        user_hash=pseudonymize_user_id("u1"),
        metric_type=MetricType.LIKE,
        value=1.0,
        timestamp=datetime.now(timezone.utc),
    )

    success = await producer.publish(evt)
    assert success is True
    assert queue.qsize() == 1

    retrieved = await consumer.consume_one(timeout=1.0)
    assert retrieved is not None
    assert retrieved.event_id == "evt_test_1"
    assert queue.empty() is True


@pytest.mark.asyncio
async def test_queue_ordering_behavior():
    """Verifies FIFO event ordering is strictly preserved through consumer batching."""
    queue = AsyncEventQueue(capacity=50)
    producer = AsyncEventProducer(queue)
    consumer = AsyncEventConsumer(queue)

    # Publish 10 sequential events
    events = [
        EngagementEvent(
            event_id=f"evt_order_{i}",
            user_hash=pseudonymize_user_id(f"u_{i}"),
            metric_type=MetricType.VIEW,
            timestamp=datetime.now(timezone.utc),
        )
        for i in range(10)
    ]

    await producer.publish_batch(events)
    assert queue.qsize() == 10

    consumed_batch = await consumer.consume_batch(max_batch_size=10, max_wait_seconds=0.5)
    assert len(consumed_batch) == 10
    
    # Assert exact FIFO order
    for idx, evt in enumerate(consumed_batch):
        assert evt.event_id == f"evt_order_{idx}"


@pytest.mark.asyncio
async def test_queue_backpressure_raise_error():
    """Tests backpressure policy RAISE_ERROR when queue reaches capacity."""
    queue = AsyncEventQueue(capacity=2, backpressure_policy=BackpressurePolicy.RAISE_ERROR)

    evt1 = EngagementEvent(
        event_id="evt_bp_1",
        user_hash=pseudonymize_user_id("u1"),
        metric_type=MetricType.CLICK,
        timestamp=datetime.now(timezone.utc),
    )
    evt2 = EngagementEvent(
        event_id="evt_bp_2",
        user_hash=pseudonymize_user_id("u2"),
        metric_type=MetricType.CLICK,
        timestamp=datetime.now(timezone.utc),
    )
    evt3 = EngagementEvent(
        event_id="evt_bp_3",
        user_hash=pseudonymize_user_id("u3"),
        metric_type=MetricType.CLICK,
        timestamp=datetime.now(timezone.utc),
    )

    await queue.put(evt1)
    await queue.put(evt2)
    assert queue.full() is True

    with pytest.raises(BackpressureException):
        await queue.put(evt3)


@pytest.mark.asyncio
async def test_queue_backpressure_drop_oldest():
    """Tests backpressure policy DROP_OLDEST when queue reaches capacity."""
    queue = AsyncEventQueue(capacity=2, backpressure_policy=BackpressurePolicy.DROP_OLDEST)

    evt1 = EngagementEvent(
        event_id="evt_drop_1",
        user_hash=pseudonymize_user_id("u1"),
        metric_type=MetricType.LIKE,
        timestamp=datetime.now(timezone.utc),
    )
    evt2 = EngagementEvent(
        event_id="evt_drop_2",
        user_hash=pseudonymize_user_id("u2"),
        metric_type=MetricType.LIKE,
        timestamp=datetime.now(timezone.utc),
    )
    evt3 = EngagementEvent(
        event_id="evt_drop_3",
        user_hash=pseudonymize_user_id("u3"),
        metric_type=MetricType.LIKE,
        timestamp=datetime.now(timezone.utc),
    )

    await queue.put(evt1)
    await queue.put(evt2)
    await queue.put(evt3)  # Evicts evt1

    assert queue.qsize() == 2
    assert queue.dropped_events_count == 1

    first_consumed = await queue.get()
    assert first_consumed.event_id == "evt_drop_2"


@pytest.mark.asyncio
async def test_ingestion_pipeline_continuous_stream():
    """Integration test for continuous IngestionPipeline execution and throughput metrics."""
    pipeline = IngestionPipeline(capacity=500, batch_size=50, batch_timeout_sec=0.1)

    consumed_events = []

    async def batch_handler(batch):
        consumed_events.extend(batch)

    pipeline.register_batch_handler(batch_handler)
    await pipeline.start_consumer_loop()

    # Generate 200 events using generator
    gen_config = EventGeneratorConfig(num_users=20, num_events=200, seed=123)
    generator = EventGenerator(gen_config)
    generated_events = generator.generate_events()

    # Produce to pipeline
    await pipeline.produce_batch(generated_events)

    # Stop pipeline
    await pipeline.stop()

    assert len(consumed_events) == 200
    metrics = pipeline.get_metrics()

    assert metrics.total_produced == 200
    assert metrics.total_consumed == 200
    assert metrics.total_rejected == 0
    assert metrics.throughput_events_per_sec > 0.0
