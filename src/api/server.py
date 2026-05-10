"""FastAPI server setup. Runs uvicorn in a daemon thread."""
import uvicorn
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.world import World

_world: World | None = None


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
    from api.routes import router
    app.include_router(router)
    return app


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
