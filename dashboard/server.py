"""Dashboard WebSocket server — pure aiohttp, zero engine dependency."""
import asyncio
import os
from aiohttp import web


async def _ws_handler(request):
    emitter = request.app["emitter"]
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    q = await emitter.register()
    stream_task = asyncio.create_task(_stream_events(emitter, ws, q))
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.ERROR:
                break
    finally:
        emitter.unregister(q)
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
        await ws.close()
    return ws


async def _stream_events(emitter, ws, q):
    """Continuously read from emitter queue and push to WebSocket."""
    try:
        while True:
            payload = await q.get()
            await ws.send_str(payload)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


async def start_dashboard(emitter, port: int = 8766):
    """Start the dashboard HTTP + WebSocket server."""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    app = web.Application()
    app["emitter"] = emitter
    app.router.add_get("/", lambda r: web.FileResponse(os.path.join(static_dir, "index.html")))
    app.router.add_get("/ws", _ws_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"  Dashboard: http://localhost:{port}")
    # Keep running until cancelled
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        await runner.cleanup()
