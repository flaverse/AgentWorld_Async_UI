"""REST + WebSocket API for external agent access.
Zero engine coupling — pure HTTP ↔ WorldGateway adapter.
"""
import asyncio

from fastapi import FastAPI, WebSocket, HTTPException, Query
from pydantic import BaseModel


class JoinRequest(BaseModel):
    agent_id: str
    agent_def: dict
    api_key: str = ""
    is_admin: bool = False


class ActRequest(BaseModel):
    agent_id: str
    decision: dict
    api_key: str = ""


class AdminRequest(BaseModel):
    api_key: str = ""
    agent_id: str = ""


def create_app(gateway, poll_interval: float = 0.3):
    app = FastAPI(title="AgentWorld Gateway")

    # ── REST ──

    @app.post("/sessions")
    async def join(req: JoinRequest):
        try:
            result = gateway.join(
                req.agent_id, req.agent_def, req.api_key, req.is_admin)
            return {"status": "ok", **result}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    @app.delete("/sessions/{agent_id}")
    async def leave(agent_id: str, api_key: str = Query("")):
        try:
            result = gateway.leave(agent_id, api_key)
            return {"status": "ok", **result}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    @app.get("/sessions")
    async def list_sessions(api_key: str = Query("")):
        try:
            return {"sessions": gateway.list_sessions(api_key)}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    @app.get("/sessions/{agent_id}/perceive")
    async def perceive(agent_id: str, api_key: str = Query("")):
        try:
            return {"status": "ok", "data": gateway.perceive(agent_id, api_key)}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    @app.post("/sessions/{agent_id}/act")
    async def act(agent_id: str, req: ActRequest, api_key: str = Query("")):
        try:
            gateway.act(agent_id, req.decision, req.api_key or api_key)
            return {"status": "ok"}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    @app.post("/world/freeze")
    async def freeze(req: AdminRequest):
        try:
            gateway.freeze(req.api_key)
            return {"status": "ok", "frozen": True}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    @app.post("/world/unfreeze")
    async def unfreeze(req: AdminRequest):
        try:
            gateway.unfreeze(req.api_key)
            return {"status": "ok", "frozen": False}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    @app.post("/sessions/{agent_id}/kick")
    async def kick(agent_id: str, req: AdminRequest):
        try:
            result = gateway.kick(agent_id or req.agent_id, req.api_key)
            return {"status": "ok", "kicked": agent_id}
        except gateway.PermissionError as e:
            raise HTTPException(403, str(e))

    # ── WebSocket ──

    @app.websocket("/session/{agent_id}")
    async def ws_session(ws: WebSocket, agent_id: str, api_key: str = Query("")):
        try:
            gateway._check_owner(agent_id, api_key)
        except gateway.PermissionError:
            await ws.close(code=4003)
            return

        await ws.accept()
        try:
            while True:
                # 1. Push perceive
                snap = gateway.perceive(agent_id, api_key)
                await ws.send_json({"type": "perceive", "data": snap})

                # 2. Wait for act
                try:
                    msg = await asyncio.wait_for(ws.receive_json(), timeout=30)
                except asyncio.TimeoutError:
                    continue  # push next perceive

                if msg.get("type") == "act":
                    gateway.act(agent_id, msg["data"], api_key)
                elif msg.get("type") == "leave":
                    break
                elif msg.get("type") == "perceive":
                    pass  # client requests another perceive without acting

                await asyncio.sleep(poll_interval)
        except Exception as e:
            print(f"  [ws] {agent_id} disconnected: {e}")
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    return app
