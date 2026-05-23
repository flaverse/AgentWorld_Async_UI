"""Director REST API — expose freeze/snap/order/take/release as HTTP endpoints.
Registered on the dashboard aiohttp app. Delete this file → zero impact on engine.
"""
from aiohttp import web


def register_director_routes(app: web.Application, director):
    """Attach Director endpoints to the aiohttp app."""

    async def _state(request):
        return web.json_response({
            "frozen": director.frozen,
            "controlled": sorted(director._controlled),
            "pending": {k: v for k, v in director._orders.items()},
        })

    async def _freeze(request):
        director.freeze()
        return web.json_response({"status": "ok", "frozen": True})

    async def _unfreeze(request):
        director.unfreeze()
        return web.json_response({"status": "ok", "frozen": False})

    async def _take(request):
        agent_id = request.match_info["agent_id"]
        director.take(agent_id)
        return web.json_response({"status": "ok", "agent_id": agent_id, "controlled": True})

    async def _release(request):
        agent_id = request.match_info["agent_id"]
        director.release(agent_id)
        return web.json_response({"status": "ok", "agent_id": agent_id, "controlled": False})

    async def _snap(request):
        agent_id = request.match_info["agent_id"]
        data = director.snap(agent_id)
        # Sanitize: convert SensorRecord objects to dicts
        if "sensory" in data and data["sensory"]:
            clean = {}
            for ch_name, ch_data in data["sensory"].items():
                clean[ch_name] = {}
                for eid, rec in (ch_data or {}).items():
                    clean[ch_name][eid] = {"name": rec.name, "distance": rec.distance, "data": rec.data}
            data["sensory"] = clean
        return web.json_response(data)

    async def _order(request):
        agent_id = request.match_info["agent_id"]
        body = await request.json()
        decision = body.get("decision", {})
        director.order(agent_id, decision)
        return web.json_response({"status": "ok", "agent_id": agent_id, "order": decision})

    app.router.add_get("/api/state", _state)
    app.router.add_post("/api/freeze", _freeze)
    app.router.add_post("/api/unfreeze", _unfreeze)
    app.router.add_post("/api/take/{agent_id}", _take)
    app.router.add_post("/api/release/{agent_id}", _release)
    app.router.add_get("/api/snap/{agent_id}", _snap)
    app.router.add_post("/api/order/{agent_id}", _order)
