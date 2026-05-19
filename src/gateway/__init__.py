"""AgentWorld Gateway — external agent access layer.

WorldGateway:  join/leave/perceive/act with permissions
API:           FastAPI REST + WebSocket
MCP:           MCP tool definitions + dispatch
"""

from .world_gateway import WorldGateway, PermissionError  # noqa: F401
from .api import create_app                                 # noqa: F401
