"""In-process pub/sub used to fan out device events to WebSocket clients."""

from __future__ import annotations

import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    async def publish(self, event: dict[str, Any]) -> None:
        for queue in list(self._queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Slow client: drop the oldest event to make room.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except Exception:
                    pass


bus = EventBus()
