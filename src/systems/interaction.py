import json
import asyncio
import uuid
from dataclasses import dataclass, field
from layers.interaction import TargetType, ResolveType


@dataclass
class ActionResult:
    target_id: str = ""
    caller_deltas: dict = field(default_factory=dict)
    target_deltas: dict = field(default_factory=dict)
    ambient_effects: list = field(default_factory=list)
    narrative: str = ""
    public_observation: str = ""
    duration: int = 0
    move_to_zone: str | None = None
    move_to_pos: list | None = None


class InteractionSystem:
    def __init__(self, resolver, sound_map: dict | None = None):
        self.resolver = resolver
        self.sound_map = sound_map or {}

    def can_interact(self, agent, target) -> bool:
        if not target.has("interaction"):
            return False
        agent_layer = agent.get("agent")
        agent_r = agent_layer.interaction_radius if agent_layer else 0
        target_r = target.get("interaction").interaction_radius
        return agent.distance_to(target) <= min(agent_r, target_r)

    def update_sensory(self, agent, all_entities: dict) -> None:
        sensory = agent.get("agent").sensory
        for eid, record in sensory.vision.items():
            if eid in all_entities:
                record.can_interact = self.can_interact(agent, all_entities[eid])

    def submit(self, interaction_id: str, agent, target, action: str,
               world) -> None:
        layer = target.get("interaction")
        act_def = layer.get_action(action)
        if not act_def:
            raise ValueError(f"Unknown action: {action}")
        if not self.can_interact(agent, target):
            raise RuntimeError(f"{agent.name} too far from {target.name}")

        agent.status = "busy"
        est_duration = act_def.estimated_duration
        agent.busy_until = world.clock.now() + est_duration

        asyncio.create_task(
            self._resolve_async(interaction_id, agent, target, action, world)
        )

    async def _resolve_async(self, iid: str, agent, target, action: str,
                             world) -> None:
        """后台裁定。resolve=rule 直接执行, resolve=llm 调裁判（含重试）。"""
        result = await self._resolve_with_retry(agent, target, action, world,
                                                 max_retries=2)
        agent.busy_result = result

    async def _resolve_with_retry(self, agent, target, action: str,
                                  world, max_retries: int = 2) -> ActionResult:
        """执行裁定。LLM 失败时带反馈重试。原则 ⑥ LLM 最小化: rule 不调 LLM。"""
        try:
            act_def = target.get("interaction").get_action(action)

            if act_def.resolve == ResolveType.RULE:
                return self._exec_rule(act_def, agent, target)

            elif act_def.resolve == ResolveType.LLM:
                ambient = world.get_ambient_entities(target, radius=2,
                                                      exclude={agent.id})
                last_raw = ""
                for attempt in range(max_retries + 1):
                    try:
                        result = await self.resolver.resolve(
                            caller=agent, target=target, action=action,
                            ambient_entities=ambient, world=world,
                        )
                        if result.narrative:
                            return result
                    except Exception as e:
                        if attempt < max_retries:
                            import asyncio as _a
                            await _a.sleep(1)
                            continue
                        raise
                    if attempt < max_retries:
                        import asyncio as _a
                        await _a.sleep(1)
                return ActionResult(target_id=target.id,
                                    narrative="裁定未产生有效结果")

            return ActionResult(target_id=target.id, narrative="unknown resolve type")

        except Exception as e:
            import traceback
            traceback.print_exc()
            return ActionResult(
                target_id=target.id,
                narrative=f"交互失败: {e}",
                public_observation=f"{agent.name}尝试{action}但出了点问题",
            )

    def apply_result(self, result: ActionResult, agent, world) -> bool:
        """处理 busy_result。返回 True 表示有有效结果。
        
        原则 ⑤ Systems 总控: 统一结果处理入口。main.py / external.py 不再重复。
        """
        if not result:
            return False

        agent.apply_deltas(result.caller_deltas)
        if result.target_id and result.target_id in world.entities:
            world.entities[result.target_id].apply_deltas(result.target_deltas)
        for amb_eff in result.ambient_effects:
            aid = amb_eff.get("entity_id", "")
            if aid in world.entities:
                world.entities[aid].apply_deltas(amb_eff.get("deltas", {}))

        if agent.has("agent"):
            agent.get("agent").memory.record(narrative=result.narrative)
            # Learn from own action
            if hasattr(agent.get("agent"), "knowledge") and agent.get("agent").knowledge:
                target_name = world.entities.get(result.target_id, None)
                target_name = target_name.name if target_name else result.target_id
                agent.get("agent").knowledge.learn_direct(
                    entity_id=result.target_id or "",
                    entity_name=target_name or "",
                    action="",  # action name not stored in ActionResult currently
                    narrative=result.narrative,
                    caller_deltas=result.caller_deltas,
                )
        agent.status = "idle"

        self._spawn_event(world, agent,
                          world.entities.get(result.target_id),
                          "", result)
        return True

    def _exec_rule(self, act_def, agent, target) -> ActionResult:
        rule = act_def.rule or {}
        return ActionResult(
            target_id=target.id,
            caller_deltas={
                **rule.get("cost", {}),
                **rule.get("effects", {}),
            },
            target_deltas={},
            ambient_effects=[],
            narrative=rule.get("narrative", "").format(caller=agent.name),
            public_observation=rule.get("narrative", "").format(caller=agent.name),
            duration=rule.get("duration_minutes", 0),
            move_to_zone=rule.get("move_to_zone"),
            move_to_pos=rule.get("move_to_pos"),
        )

    def _spawn_event(self, world, agent, target, action, result) -> None:
        from entity.event_entity import EventEntity
        from layers.visual import VisualLayer
        from layers.auditory import AuditoryLayer

        sound = self.sound_map.get(action, "")
        layers = {
            "visual": VisualLayer(
                visible_radius=8, sprite=None,
                info={"look": f"{agent.name}正在{action}"}
            ),
        }
        if sound:
            layers["auditory"] = AuditoryLayer(
                audible_radius=12, info={"sound": sound}
            )

        event = EventEntity(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            name=f"{agent.name}的交互",
            zone=target.zone, pos=list(target.pos),
            spawned_at=world.clock.now(),
            lifespan_minutes=3,
            source_entity_id=agent.id, source_action=action,
            layers=layers,
        )
        world.spawn_event(event)
