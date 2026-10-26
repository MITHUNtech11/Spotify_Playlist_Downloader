import asyncio
import threading
from typing import Set, Dict, Any, Optional, Tuple

class EventBus:
    """Thread-safe event broadcast bus for Server-Sent Events (SSE)."""
    def __init__(self):
        self.lock = threading.Lock()
        self.subscribers: Set[Tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
            
        with self.lock:
            self.subscribers.add((queue, loop))
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        with self.lock:
            self.subscribers = {item for item in self.subscribers if item[0] is not queue}

    def publish(self, event: Dict[str, Any]):
        """Publish an event to all connected subscriber queues from any thread."""
        with self.lock:
            subs = list(self.subscribers)

        for queue, loop in subs:
            try:
                if loop.is_running():
                    loop.call_soon_threadsafe(queue.put_nowait, event)
                else:
                    queue.put_nowait(event)
            except Exception:
                pass

event_bus = EventBus()
