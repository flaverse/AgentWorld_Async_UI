"""DashboardEmitter — collect agent events and broadcast to WebSocket clients.
Zero coupling to engine logic. Pure event relay.
"""
import asyncio
import time
import json


class DashboardEmitter:
    def __init__(self, history_size: int = 50):
        self._clients: list[asyncio.Queue] = []
        self._history: list[dict] = []
        self._history_size = history_size
        self._start_ts = time.time()

    async def register(self) -> asyncio.Queue:
        """Register a new WebSocket client. Returns a queue for streaming events."""
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._clients.append(q)
        # Send catch-up history
        for event in self._history:
            await q.put(event)
        return q

    def unregister(self, q: asyncio.Queue):
        """Remove a disconnected client."""
        if q in self._clients:
            self._clients.remove(q)

    def emit(self, event: dict):
        """Push an event to all connected clients (fire-and-forget)."""
        event["ts"] = round(time.time() - self._start_ts, 1)
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history.pop(0)
        payload = json.dumps(event, ensure_ascii=False)
        for q in self._clients:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass
