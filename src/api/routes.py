"""REST API routes for external agent access."""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from api.schemas import (
    AgentRegisterRequest, AgentMoveRequest, InteractRequest, CommandRequest,
    WorldStateResponse,
)
from api.ws import manager
from core.world import World
import uuid
import asyncio
import json
import traceback

router = APIRouter(prefix="/api/v1")


# ── Error reporting ──

@router.get("/errors")
async def get_errors():
    """Get recent error log from the collector."""
    from core.error_collector import errors
    return errors.get_summary()

@router.delete("/errors")
async def clear_errors():
    from core.error_collector import errors
    errors.clear()
    return {"status": "cleared"}


def safe_handler(fn):
    """Decorator: wraps any route to catch unexpected errors."""
    from functools import wraps
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            from core.error_collector import errors
            errors.log_exception(f"api.{fn.__name__}", e)
            raise HTTPException(500, f"Internal error: {e}")
    return wrapper


def get_world() -> World:
    from api.server import _world
    if _world is None:
        raise HTTPException(500, "World not initialized")
    return _world


# ── World state ──

@safe_handler
@router.get("/world/state")
async def get_world_state(focus: str | None = None):
    world = get_world()
    entities_out = []
    for e in world.entities.values():
        ent_data = {
            "id": e.id, "name": e.name, "zone": e.zone, "pos": e.pos,
            "status": e.status,
        }
        if e.has("visual"):
            v = e.get("visual")
            ent_data["sprite"] = v.sprite
            ent_data["sprite_sheet"] = v.sprite_sheet
        if e.has("interaction"):
            inter = e.get("interaction")
            ent_data["public_attrs"] = inter.public_attrs
            ent_data["actions"] = list(inter.actions.keys())
        if e.has("agent"):
            ag = e.get("agent")
            ent_data["autonomous"] = ag.autonomous
        entities_out.append(ent_data)

    return {
        "time": world.clock.time_str(),
        "zones": list(world.zones.values()),
        "entities": entities_out,
    }


# ── Agent registration ──

@safe_handler
@router.post("/agents")
async def register_agent(req: AgentRegisterRequest):
    world = get_world()
    if req.id in world.entities:
        raise HTTPException(400, f"Agent {req.id} already exists")

    entity = world.register_external_agent(
        agent_id=req.id,
        name=req.name,
        zone=req.zone,
        pos=req.pos,
        sprite=req.sprite or f"ext_{req.id[:6]}",
        personality=req.personality or "来访者",
    )
    return {"id": entity.id, "status": "registered", "pos": entity.pos}


# ── Agent actions ──

@safe_handler
@router.post("/agents/{agent_id}/move")
async def move_agent(agent_id: str, req: AgentMoveRequest):
    world = get_world()
    entity = world.entities.get(agent_id)
    if not entity:
        raise HTTPException(404, "Agent not found")

    from_pos = list(entity.pos)
    move_time = entity.move_to(req.to)

    systems = world.get_systems()
    systems["sensory"].update(entity, world.entities)
    systems["interaction"].update_sensory(entity, world.entities)

    # Push sensory to this agent
    sensory = entity.get("agent").sensory if entity.has("agent") else None
    if sensory:
        await _push_sensory(agent_id, entity, world, systems)

    # Broadcast move to others
    await manager.broadcast_to_all_external({
        "event": "agent_move",
        "agent": agent_id,
        "from": from_pos,
        "to": req.to,
        "facing": entity.calc_facing(req.to),
        "zone": entity.zone,
    })

    return {"status": "moved", "pos": entity.pos, "duration_minutes": move_time}


@safe_handler
@router.post("/agents/{agent_id}/interact")
async def interact_agent(agent_id: str, req: InteractRequest):
    world = get_world()
    entity = world.entities.get(agent_id)
    if not entity:
        raise HTTPException(404, "Agent not found")

    target = world.entities.get(req.target_entity)
    if not target:
        raise HTTPException(404, f"Target {req.target_entity} not found")

    systems = world.get_systems()
    if not systems["interaction"].can_interact(entity, target):
        raise HTTPException(400, f"Target not in interaction range")

    iid = uuid.uuid4().hex[:8]
    try:
        systems["interaction"].submit(iid, entity, target, req.action, world)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(400, str(e))

    return {"status": "submitted", "interaction_id": iid}


@safe_handler
@router.post("/agents/{agent_id}/command")
async def command_agent(agent_id: str, req: CommandRequest):
    """人类向自主 agent 发指令 → 写入 inbox。"""
    world = get_world()
    entity = world.entities.get(agent_id)
    if not entity or not entity.has("agent"):
        raise HTTPException(404, "Agent not found or not autonomous")

    entity.get("agent").inbox.send(
        from_id="human", from_name="人类", method="command",
        content=req.content,
    )
    return {"status": "sent"}


# ── Sensory poll ──

@safe_handler
@router.post("/agents/{agent_id}/sensory")
async def get_sensory(agent_id: str):
    """主动拉取当前感知数据。"""
    world = get_world()
    entity = world.entities.get(agent_id)
    if not entity:
        raise HTTPException(404, "Agent not found")

    systems = world.get_systems()
    systems["sensory"].update(entity, world.entities)
    systems["interaction"].update_sensory(entity, world.entities)

    return await _build_sensory_response(agent_id, entity, world, systems)


async def _push_sensory(agent_id: str, entity, world, systems):
    data = await _build_sensory_response(agent_id, entity, world, systems)
    await manager.send_to_agent(agent_id, data)


async def _build_sensory_response(agent_id: str, entity, world, systems):
    agent_layer = entity.get("agent") if entity.has("agent") else None
    sensory = agent_layer.sensory if agent_layer else None

    interactable_out = []
    visible_out = []

    if sensory:
        for r in sensory.get_interactable():
            target = world.entities.get(r.entity_id)
            actions = []
            if target and target.has("interaction"):
                actions = list(target.get("interaction").actions.keys())
            interactable_out.append({
                "id": r.entity_id, "name": r.name, "pos": r.pos,
                "distance": r.distance, "visual": r.visual_data,
                "actions": actions, "can_interact": True,
            })
        for r in sensory.get_visible_only():
            target = world.entities.get(r.entity_id)
            actions = []
            if target and target.has("interaction"):
                actions = list(target.get("interaction").actions.keys())
            visible_out.append({
                "id": r.entity_id, "name": r.name, "pos": r.pos,
                "distance": r.distance, "visual": r.visual_data,
                "actions": actions, "can_interact": False,
            })

    return {
        "type": "sensory_update",
        "agent_id": agent_id,
        "pos": entity.pos,
        "zone": entity.zone,
        "interactable": interactable_out,
        "visible": visible_out,
    }


# ── WebSocket ──

@router.websocket("/ws/agent/{agent_id}")
async def ws_agent(ws: WebSocket, agent_id: str):
    from agent.external import ExternalAgentProxy

    await ws.accept()
    world = get_world()

    # Check if agent exists; if not, auto-create a temporary one
    entity = world.entities.get(agent_id)
    if not entity:
        zone_ids = list(world.zones.keys())
        default_zone = zone_ids[0] if zone_ids else "bar_zone"
        entity = world.register_external_agent(
            agent_id=agent_id,
            name=f"访客_{agent_id[:6]}",
            zone=default_zone,
            pos=[5, 5],
            sprite=None,
            personality="外部来访者",
        )

    proxy = ExternalAgentProxy(ws, entity, world, world.get_systems())
    await manager.register_agent(agent_id, ws, proxy)

    try:
        # Push initial sensory
        await _push_sensory(agent_id, entity, world, world.get_systems())

        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"error": "invalid json"})
                continue
            await proxy.handle_message(msg)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.unregister_agent(agent_id)
