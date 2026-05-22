"""AgentWorld Gateway — external agent access layer.

WorldGateway:  join/leave/perceive/act with permissions
API:           FastAPI REST + WebSocket
"""

from .world_gateway import WorldGateway, PermissionError  # noqa: F401
from .api import create_app                                 # noqa: F401
