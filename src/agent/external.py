"""ExternalAgentProxy — bridge between WebSocket and World Systems."""
import json
import uuid
from entity.entity import Entity


class ExternalAgentProxy:
    """桥接层: 收 WS 消息 → 调现有 Systems → 推回 WS。

    模式 1 — 人类操控:    1 个 WS 连 1 个 Entity。人类手动发 move/interact
    模式 2 — 远程 AI:     另一进程跑 LLM → 通过 HTTP/WS 调这里的 Entity
    模式 3 — 被动观察:    只收 sensory，不发指令
    """

    def __init__(self, ws, entity: Entity, world, systems: dict):
        self.ws = ws
        self.entity = entity
        self.world = world
        self.systems = systems

    async def handle_message(self, msg: dict):
        msg_type = msg.get("type", "")

        if msg_type == "move":
            await self._handle_move(msg)
        elif msg_type == "interact":
            await self._handle_interact(msg)
        elif msg_type == "sensory":
            await self._handle_sensory_request()
        elif msg_type == "command":
            await self._handle_command(msg)
        else:
            await self.ws.send_json({"error": f"unknown type: {msg_type}"})

    async def _handle_move(self, msg: dict):
        to = msg.get("to")
        if not to or len(to) != 2:
            await self.ws.send_json({"error": "to must be [x, y]"})
            return

        from_pos = list(self.entity.pos)
        move_time = self.entity.move_to(to)

        # 移动后重新感知
        self.systems["sensory"].update(self.entity, self.world.entities)
        self.systems["interaction"].update_sensory(self.entity, self.world.entities)

        # 推送感官
        await self._push_sensory()

        # 广播移动
        from api.ws import manager
        await manager.broadcast_to_all_external({
            "event": "agent_move",
            "agent": self.entity.id,
            "from": from_pos,
            "to": to,
            "facing": self.entity.calc_facing(to),
            "zone": self.entity.zone,
        })

        await self.ws.send_json({
            "type": "move_ack",
            "pos": self.entity.pos,
            "duration_minutes": move_time,
        })

    async def _handle_interact(self, msg: dict):
        target_id = msg.get("target_entity")
        action = msg.get("action")
        if not target_id or not action:
            await self.ws.send_json({"error": "target_entity and action required"})
            return

        target = self.world.entities.get(target_id)
        if not target:
            await self.ws.send_json({"error": f"target {target_id} not found"})
            return

        if not self.systems["interaction"].can_interact(self.entity, target):
            await self.ws.send_json({"error": "target not in range"})
            return

        iid = uuid.uuid4().hex[:8]
        self.systems["interaction"].submit(iid, self.entity, target, action, self.world)

        await self.ws.send_json({
            "type": "interact_ack",
            "interaction_id": iid,
            "target": target_id,
            "action": action,
            "status": "submitted (busy)",
        })

        # 等结果 (简单轮询, busy_result 由 resolver 写入)
        # busy_until 之后检查
        import asyncio
        for _ in range(30):
            await asyncio.sleep(0.5)
            if self.entity.busy_result is not None:
                result = self.entity.busy_result
                self.entity.busy_result = None

                self.entity.apply_deltas(result.caller_deltas)
                if self.entity.has("agent"):
                    self.entity.get("agent").drives.apply_deltas(result.caller_deltas)
                if result.target_id and result.target_id in self.world.entities:
                    self.world.entities[result.target_id].apply_deltas(result.target_deltas)
                for amb_eff in result.ambient_effects:
                    aid = amb_eff.get("entity_id", "")
                    if aid in self.world.entities:
                        self.world.entities[aid].apply_deltas(amb_eff.get("deltas", {}))

                if self.entity.has("agent"):
                    self.entity.get("agent").memory.record(narrative=result.narrative)
                self.entity.status = "idle"

                await self.ws.send_json({
                    "type": "interaction_result",
                    "action": action,
                    "target": target_id,
                    "narrative": result.narrative,
                    "caller_deltas": result.caller_deltas,
                    "public_observation": result.public_observation,
                })

                # 广播
                from api.ws import manager
                await manager.broadcast_to_all_external({
                    "event": "interaction_complete",
                    "agent": self.entity.id,
                    "target": target_id,
                    "action": action,
                    "observation": result.public_observation,
                })
                break

            if self.entity.status == "idle" and self.entity.busy_result is None:
                break

    async def _handle_sensory_request(self):
        self.systems["sensory"].update(self.entity, self.world.entities)
        self.systems["interaction"].update_sensory(self.entity, self.world.entities)
        await self._push_sensory()

    async def _handle_command(self, msg: dict):
        """外部人类向自身 Entity 发自定义命令。当前仅 echo。"""
        content = msg.get("content", "")
        await self.ws.send_json({
            "type": "command_ack",
            "msg": f"received: {content}",
        })

    async def _push_sensory(self):
        """构建并推送感知数据。"""
        agent_layer = self.entity.get("agent") if self.entity.has("agent") else None
        sensory = agent_layer.sensory if agent_layer else None

        interactable_out = []
        visible_out = []

        if sensory:
            for r in sensory.get_interactable():
                target = self.world.entities.get(r.entity_id)
                actions = []
                if target and target.has("interaction"):
                    actions = list(target.get("interaction").actions.keys())
                interactable_out.append({
                    "id": r.entity_id, "name": r.name, "pos": r.pos,
                    "distance": r.distance, "visual": r.visual_data,
                    "actions": actions,
                })
            for r in sensory.get_visible_only():
                target = self.world.entities.get(r.entity_id)
                actions = []
                if target and target.has("interaction"):
                    actions = list(target.get("interaction").actions.keys())
                visible_out.append({
                    "id": r.entity_id, "name": r.name, "pos": r.pos,
                    "distance": r.distance, "visual": r.visual_data,
                    "actions": actions,
                })

        await self.ws.send_json({
            "type": "sensory_update",
            "agent_id": self.entity.id,
            "pos": self.entity.pos,
            "zone": self.entity.zone,
            "interactable": interactable_out,
            "visible": visible_out,
        })
