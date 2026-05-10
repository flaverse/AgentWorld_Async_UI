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
        try:
            act_def = target.get("interaction").get_action(action)

            if act_def.resolve == ResolveType.RULE:
                result = self._exec_rule(act_def, agent, target)
            elif act_def.resolve == ResolveType.LLM:
                ambient = world.get_ambient_entities(target, radius=2,
                                                      exclude={agent.id})
                result = await self.resolver.resolve(
                    caller=agent, target=target, action=action,
                    ambient_entities=ambient, world=world,
                )
            else:
                result = ActionResult(narrative="unknown resolve type")
        except Exception as e:
            result = ActionResult(
                target_id=target.id,
                narrative=f"交互失败: {e}",
                public_observation=f"{agent.name}尝试{action}但出了点问题",
            )
            import traceback
            traceback.print_exc()

        agent.busy_result = result
        try:
            self._spawn_event(world, agent, target, action, result)
        except Exception:
            pass

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
