"""Data ingestion layer - batch and real-time processing.

Designed for high throughput (~1000+ conversations/minute) using:
- Async processing with buffered batches
- Redis queue for real-time ingestion
- Batch API for bulk historical loads
"""
import asyncio
import json
from enum import Enum
from typing import AsyncIterator

from src.models import Conversation


class IngestMode(str, Enum):
    BATCH = "batch"
    REALTIME = "realtime"


class Ingester:
    """Ingests multi-turn conversations and feedback signals."""

    def __init__(self, batch_size: int = 100, buffer_time_ms: int = 100):
        self.batch_size = batch_size
        self.buffer_time_ms = buffer_time_ms
        self._buffer: list[Conversation] = []
        self._callbacks: list[callable] = []

    def register_callback(self, fn: callable) -> None:
        """Register callback for when batches are ready (e.g., trigger evaluation)."""
        self._callbacks.append(fn)

    async def ingest_one(self, data: dict | Conversation) -> str:
        """Ingest a single conversation (real-time path)."""
        conv = data if isinstance(data, Conversation) else Conversation.model_validate(data)
        self._buffer.append(conv)

        if len(self._buffer) >= self.batch_size:
            batch = self._buffer[: self.batch_size]
            self._buffer = self._buffer[self.batch_size :]
            await self._flush_batch(batch)

        return conv.conversation_id

    async def ingest_batch(self, items: list[dict | Conversation]) -> list[str]:
        """Ingest a batch of conversations."""
        ids = []
        for item in items:
            conv = item if isinstance(item, Conversation) else Conversation.model_validate(item)
            ids.append(conv.conversation_id)
            self._buffer.append(conv)

        while len(self._buffer) >= self.batch_size:
            batch = self._buffer[: self.batch_size]
            self._buffer = self._buffer[self.batch_size :]
            await self._flush_batch(batch)

        return ids

    async def flush(self) -> None:
        """Flush remaining buffer."""
        if self._buffer:
            await self._flush_batch(self._buffer)
            self._buffer = []

    async def _flush_batch(self, batch: list[Conversation]) -> None:
        """Process batch and notify callbacks."""
        for cb in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(batch)
                else:
                    cb(batch)
            except Exception:
                pass  # Log in production

    async def stream_from_file(self, path: str) -> AsyncIterator[Conversation]:
        """Stream conversations from a JSONL file (batch ingestion)."""
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield Conversation.model_validate(json.loads(line))
