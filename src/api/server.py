"""FastAPI server setup. Static file serving + global WS broadcast."""
import os
import uvicorn
import threading
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.world import World

_world: World | None = None
_global_ws_clients: list = []


def create_app(world: World) -> FastAPI:
    global _world
    _world = world

    app = FastAPI(title="AgentWorld Async API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files (frontend)
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "web")
    web_dir = os.path.abspath(web_dir)
    if os.path.isdir(web_dir):
        app.mount("/web", StaticFiles(directory=web_dir), name="web")
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="root")

    from api.routes import router
    app.include_router(router)
    return app


def add_global_ws_client(ws):
    _global_ws_clients.append(ws)


def remove_global_ws_client(ws):
    if ws in _global_ws_clients:
        _global_ws_clients.remove(ws)


async def broadcast_to_frontend(data: dict):
    """Send event to ALL connected frontend observers."""
    import json
    dead = []
    for ws in _global_ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        remove_global_ws_client(ws)


def start_api_server(world: World, host: str = "0.0.0.0", port: int = 8000):
    """Start uvicorn in a daemon thread. Non-blocking."""
    app = create_app(world)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    def run_server():
        import asyncio as _asyncio
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return t
