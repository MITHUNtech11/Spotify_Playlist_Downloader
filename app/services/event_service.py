import asyncio
from typing import Set, Dict, Any, Optional

class EventBus:
    """Thread-safe event broadcast bus for Server-Sent Events (SSE)."""
    def __init__(self):
        self.subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    def publish(self, event: Dict[str, Any]):
        """Publish an event to all connected subscriber queues."""
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(event)
            except Exception:
                pass

event_bus = EventBus()
