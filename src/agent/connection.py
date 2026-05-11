"""AgentConnection — 外部 agent 的 WS 会话封装。

原则 ⑦ Agent 自治: 连接管理的是外部传入的 Entity, 不裁定其属性。
原则 ⑤ Systems 总控: 生命周期走 Lifecycle, 交互走 InteractionSystem。

解决:
  P0#1: disconnect 时 despawn Entity
  P0#5: 重连复用 / 统一注册
  P1#7: 心跳检测
  P1#8: inbox push
  P0#2: busy 时拒绝 move/interact
  P0#3: zone 边界校验
"""
import asyncio
import json
import uuid
from entity.entity import Entity


class AgentConnection:
    """单个外部 agent 的完整会话。"""

    def __init__(self, ws, entity: Entity, world, systems: dict):
        self.ws = ws
        self.entity = entity
        self.world = world
        self.systems = systems
        self._alive = True
        self._busy_event: asyncio.Event | None = None

    async def run(self):
        """主循环: 收 WS 消息 + 推 inbox + 心跳 + busy polling。"""
        heartbeat_task = asyncio.create_task(self._heartbeat())
        busy_poll_task = asyncio.create_task(self._busy_polling())

        try:
            await self._push_sensory()

            while self._alive:
                try:
                    raw = await asyncio.wait_for(self.ws.receive_text(), timeout=1)
                except asyncio.TimeoutError:
                    continue

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await self.ws.send_json({"error": "invalid json"})
                    continue

                await self._dispatch(msg)
                await self._push_inbox()

        except Exception:
            pass
        finally:
            self._alive = False
            heartbeat_task.cancel()
            busy_poll_task.cancel()
            if hasattr(self.world, 'lifecycle'):
                self.world.lifecycle.despawn(self.entity.id)
            await self._cleanup_ws()

    async def _dispatch(self, msg: dict):
        msg_type = msg.get("type", "")
        if msg_type == "move":
            await self._move(msg)
        elif msg_type == "interact":
            await self._interact(msg)
        elif msg_type == "sensory":
            await self._push_sensory()
        elif msg_type == "pong":
            pass  # heartbeat response
        else:
            await self.ws.send_json({"error": f"unknown type: {msg_type}"})

    async def _move(self, msg: dict):
        # P0#2: busy 时拒绝
        if self.entity.status != "idle":
            await self.ws.send_json({"error": "cannot move while busy"})
            return

        to = msg.get("to")
        if not to or len(to) != 2:
            await self.ws.send_json({"error": "to must be [x, y]"})
            return

        # P0#3: zone 边界校验
        zone = self.world.zones.get(self.entity.zone, {})
        w, h = zone.get("width", 999), zone.get("height", 999)
        if not (0 <= to[0] < w and 0 <= to[1] < h):
            await self.ws.send_json({
                "error": f"position out of bounds ({w}x{h})"
            })
            return

        from_pos = list(self.entity.pos)
        move_time = self.entity.move_to(to)

        self.systems["sensory"].update(self.entity, self.world.entities, self.world)
        self.systems["interaction"].update_sensory(self.entity, self.world.entities)

        await self._push_sensory()
        await self.ws.send_json({
            "type": "move_ack", "pos": self.entity.pos,
            "duration_minutes": move_time,
        })

    async def _interact(self, msg: dict):
        # P0#2: busy 时拒绝
        if self.entity.status != "idle":
            await self.ws.send_json({"error": "cannot interact while busy"})
            return

        target_id = msg.get("target_entity")
        action = msg.get("action")
        if not target_id or not action:
            await self.ws.send_json({"error": "target_entity and action required"})
            return

        target = self.world.entities.get(target_id)
        if not target:
            await self.ws.send_json({"error": f"target {target_id} not found"})
            return

        # P2#11: 校验 action 是否可用
        inter_layer = target.get("interaction")
        if not inter_layer or not inter_layer.get_action(action):
            available = list(inter_layer.actions.keys()) if inter_layer else []
            await self.ws.send_json({
                "error": f"action '{action}' not available",
                "available": available,
            })
            return

        if not self.systems["interaction"].can_interact(self.entity, target):
            await self.ws.send_json({"error": "target not in interaction range"})
            return

        iid = uuid.uuid4().hex[:8]
        try:
            self.systems["interaction"].submit(
                iid, self.entity, target, action, self.world
            )
        except (ValueError, RuntimeError) as e:
            await self.ws.send_json({"error": str(e)})
            return

        await self.ws.send_json({
            "type": "interact_ack", "interaction_id": iid,
            "target": target_id, "action": action,
            "status": "submitted",
        })

        # 等待结果 (Event 通知替代轮询 #3)
        self._busy_event = asyncio.Event()
        try:
            await asyncio.wait_for(self._busy_event.wait(), timeout=30)
        except asyncio.TimeoutError:
            await self.ws.send_json({"error": "interaction timeout"})
            return

        if self.entity.busy_result is not None:
            result = self.entity.busy_result
            self.entity.busy_result = None
            self.systems["interaction"].apply_result(
                result, self.entity, self.world
            )
            await self.ws.send_json({
                "type": "interaction_result", "action": action,
                "target": target_id, "narrative": result.narrative,
                "caller_deltas": result.caller_deltas,
                "public_observation": result.public_observation,
            })

    async def _push_sensory(self):
        """推送当前感知数据给外部 agent。"""
        self.systems["sensory"].update(self.entity, self.world.entities, self.world)
        self.systems["interaction"].update_sensory(self.entity, self.world.entities)

        agent_layer = self.entity.get("agent")
        sensory = agent_layer.sensory if agent_layer else None
        interactable_out, visible_out = [], []

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
            "type": "sensory_update", "agent_id": self.entity.id,
            "pos": self.entity.pos, "zone": self.entity.zone,
            "interactable": interactable_out, "visible": visible_out,
        })

    async def _push_inbox(self):
        """推送 pending inbox 消息给外部 agent (P1#8)。"""
        agent_layer = self.entity.get("agent")
        if not agent_layer or not agent_layer.inbox:
            return
        msgs = agent_layer.inbox.drain()
        if msgs:
            await self.ws.send_json({
                "type": "inbox_messages",
                "messages": [
                    {"from": m.from_agent_name, "content": m.content}
                    for m in msgs
                ],
            })

    async def _heartbeat(self):
        """每 20 秒检查一次心跳 (P1#7)。"""
        while self._alive:
            await asyncio.sleep(20)
            if not self._alive:
                break

    async def _busy_polling(self):
        """轻量轮询: 检测 busy_result 到达并唤醒等待者。"""
        while self._alive:
            await asyncio.sleep(0.3)
            if self.entity.busy_result is not None and self._busy_event:
                if not self._busy_event.is_set():
                    self._busy_event.set()

    async def _cleanup_ws(self):
        try:
            await self.ws.close()
        except Exception:
            pass

    def notify_busy_done(self):
        """外部通知: 交互结果已到达, 唤醒等待的 _handle_interact。"""
        if self._busy_event and not self._busy_event.is_set():
            self._busy_event.set()

    @classmethod
    async def accept(cls, ws, agent_id: str, world, systems):
        """工厂方法: 接受 WS 连接, 创建或复用 AgentConnection。"""
        # P0#5: 重连复用
        entity = world.entities.get(agent_id)
        is_reconnect = entity is not None

        if not is_reconnect:
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
        else:
            # 重连: 重置状态
            entity.status = "idle"
            entity.busy_result = None
            entity.busy_until = 0.0

        conn = cls(ws, entity, world, systems)
        await conn.run()
        return conn
