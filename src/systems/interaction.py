import json
import asyncio
import uuid
from dataclasses import dataclass, field
from layers.interaction import TargetType, ResolveType, ActionDef


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

    def build_component(self, center, all_entities: dict, radius: int = 3) -> list[dict]:
        """构建交互分量: 从 center 出发，空间 BFS 收集半径内所有实体。
        
        返回: [{entity_id, name, describe, private_attrs}, ...]
        用于 Story/Projection 管线的 context 构建。
        """
        component = []
        seen = {center.id}
        
        # ① 中心实体
        comp = self._entity_to_component_entry(center)
        if comp:
            component.append(comp)
        
        # ② 半径 R 内的所有实体
        for e in all_entities.values():
            if e.id in seen or e.zone != center.zone:
                continue
            d = center.distance_to(e)
            if d <= radius:
                seen.add(e.id)
                comp = self._entity_to_component_entry(e)
                if comp:
                    component.append(comp)
        
        return component
    
    def _entity_to_component_entry(self, entity) -> dict | None:
        """将 Entity 转换为 component entry dict。"""
        desc = getattr(entity, 'describe', None) or entity.name
        attrs = {}
        inter = entity.get("interaction")
        if inter:
            attrs = inter.private_attrs.copy()
            # Add public info
            if inter.public_attrs:
                desc += f" [{inter.public_attrs}]"
        
        return {
            "entity_id": entity.id,
            "name": entity.name,
            "describe": desc,
            "private_attrs": attrs,
            "is_agent": entity.has("agent") and entity.get("agent").autonomous,
        }

    def submit(self, interaction_id: str, agent, target, action: str,
               world) -> None:
        layer = target.get("interaction")
        act_def = layer.get_action(action) if layer else None
        
        # Free-text action support: if no predefined action, treat as llm-resolved
        if not act_def:
            if layer:  # entity has interaction layer but action not in list
                act_def = ActionDef(
                    method=action,
                    target_type=TargetType.PASSIVE,
                    resolve=ResolveType.LLM,
                    estimated_duration=10,
                )
                layer.actions[action] = act_def  # Store for _resolve_async lookup
            else:
                raise ValueError(f"No interaction layer on {target.name}")
                
        if not self.can_interact(agent, target):
            raise RuntimeError(f"{agent.name} too far from {target.name}")

        agent.status = "busy"
        est_duration = act_def.estimated_duration
        agent.busy_until = world.clock.now() + est_duration

        asyncio.create_task(
            self._resolve_async(interaction_id, agent, target, action, world)
        ).add_done_callback(
            lambda t: self._on_task_done(t, agent, target, action, world)
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
            from core.error_collector import errors
            errors.log_exception("interaction._resolve_with_retry", e,
                                 f"{agent.name} -> {target.name}.{action}")
            return ActionResult(
                target_id=target.id,
                narrative=f"交互失败: {e}",
                public_observation=f"{agent.name}尝试{action}但出了点问题",
            )

    def _on_task_done(self, task, agent, target, action, world):
        """Callback: if the async runner task crashed, mark agent idle and log."""
        if task.exception():
            from core.error_collector import errors
            errors.log_task_failure(f"interaction.resolve({agent.name},{action})",
                                    task.exception())
            agent.status = "idle"
            agent.busy_result = ActionResult(
                target_id=target.id,
                narrative=f"内部错误: 裁定未完成",
                public_observation=f"{agent.name}的交互出了点问题",
            )

    def apply_result(self, result: ActionResult, agent, world) -> bool:
        """处理 busy_result。返回 True 表示有有效结果。
        
        原则 ⑤ Systems 总控: 统一结果处理入口。
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
            if hasattr(agent.get("agent"), "knowledge") and agent.get("agent").knowledge:
                target_name = world.entities.get(result.target_id, None)
                target_name = target_name.name if target_name else result.target_id
                agent.get("agent").knowledge.learn_direct(
                    entity_id=result.target_id or "",
                    entity_name=target_name or "",
                    action="",
                    narrative=result.narrative,
                    caller_deltas=result.caller_deltas,
                )

        # Gate传送: 使用 Lifecycle.transfer_zone (P1#6)
        if result.move_to_zone:
            if hasattr(world, 'lifecycle'):
                world.lifecycle.transfer_zone(agent, result.move_to_zone,
                                              result.move_to_pos or agent.pos)
            else:
                agent.zone = result.move_to_zone
                agent.pos = result.move_to_pos or agent.pos
                if agent.has("agent"):
                    agent.get("agent").sensory.clear()

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
