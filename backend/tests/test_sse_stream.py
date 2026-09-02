"""
Unit Tests for Server-Sent Events (SSE) Streaming Router.
"""

import pytest
from app.api.routes.stream import sse_event_generator


@pytest.mark.asyncio
async def test_sse_stream_generator_format():
    """Tests sse_event_generator output formatting."""
    gen = sse_event_generator()
    first_chunk = await anext(gen)

    assert first_chunk.startswith("data: ")
    assert "composite_score" in first_chunk
    assert "policy_t0" in first_chunk
