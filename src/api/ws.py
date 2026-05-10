"""WebSocket manager: per-agent channels + broadcast."""
from fastapi import WebSocket
from typing import Any
import json
import uuid


class ConnectionManager:
    """Manage WebSocket connections for external agents."""

    def __init__(self):
        self.agent_ws: dict[str, WebSocket] = {}
        self.external_proxies: dict[str, Any] = {}

    async def register_agent(self, agent_id: str, ws: WebSocket, proxy: Any):
        self.agent_ws[agent_id] = ws
        self.external_proxies[agent_id] = proxy

    async def unregister_agent(self, agent_id: str):
        self.agent_ws.pop(agent_id, None)
        self.external_proxies.pop(agent_id, None)

    async def send_to_agent(self, agent_id: str, data: dict):
        ws = self.agent_ws.get(agent_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                await self.unregister_agent(agent_id)

    async def broadcast_to_all_external(self, data: dict):
        for agent_id in list(self.agent_ws.keys()):
            await self.send_to_agent(agent_id, data)


manager = ConnectionManager()
