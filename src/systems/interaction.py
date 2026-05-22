"""InteractionSystem — 统一交互模型
interact() 是唯一入口。NPC→NPC: 纯同步写层。NPC→Item: +1 LLM。
"""
import json
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    target_id: str = ""
    caller_deltas: dict = field(default_factory=dict)
    narrative: str = ""
    llm2_prompt: str = ""
    llm2_output: str = ""


class InteractionSystem:
    def __init__(self, llm=None, assembler=None):
        self.llm = llm
        self.assembler = assembler

    # ═══════════ public API ═══════════

    def can_interact(self, agent, target) -> bool:
        if not target.has("interaction"):
            return False
        agent_layer = agent.get("agent")
        agent_r = agent_layer.interaction_radius if agent_layer else 0
        target_r = target.get("interaction").interaction_radius
        return agent.distance_to(target) <= min(agent_r, target_r)

    def find_entity_by_name(self, zone: str, name: str,
                             all_entities: dict, exclude_id: str = "") -> object | None:
        """Exact name match — no fuzzy, no guessing. Returns entity or None.
        If multiple entities share the same name in the zone, returns None (ambiguous).
        """
        match = None
        for e in all_entities.values():
            if e.zone != zone or not e.has("interaction"):
                continue
            if e.id == exclude_id:
                continue
            if e.name == name:
                if match is not None:
                    return None  # duplicate name — ambiguous, let LLM resolve
                match = e
        return match

    def find_entity_at(self, zone: str, pos: list[int], action: str,
                       all_entities: dict, exclude_id: str = "") -> object | None:
        """Deprecated — use find_entity_by_name with LLM-supplied target_name."""
        candidates = []
        for e in all_entities.values():
            if e.zone != zone or not e.has("interaction"):
                continue
            if e.id == exclude_id:
                continue
            d = abs(pos[0] - e.pos[0]) + abs(pos[1] - e.pos[1])
            candidates.append((d, e))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        for d, e in candidates:
            if e.name in action:
                return e
        return None

    # ═══════════ core: interact() ═══════════

    async def interact(self, agent, target,
                       decision: dict, world) -> ActionResult | None:
        """统一交互入口。同步写层，NPC→Item 加一次 LLM。"""
        target_inter = target.get("interaction")

        agent_layer = agent.get("agent")
        dialogue = decision.get("dialogue", "")
        visual = decision.get("visual", "")
        self_deltas = decision.get("self_deltas", {})
        story = decision.get("story", "")

        # ① Write agent's layers (observers poll)
        self._write_agent_layers(agent, agent_layer, decision, dialogue, visual)

        # ② Apply self_deltas
        if self_deltas:
            self._apply_deltas(agent, self_deltas)

        if agent_layer:
            agent_layer._write_pending = True
            if decision.get("expects_reply"):
                agent_layer._reply_deadline = time.time() + decision.get("patience", 5)

        # ③ NPC→NPC: done
        if target.has("agent"):
            return ActionResult(
                target_id=target.id,
                caller_deltas=self_deltas,
                narrative=story or f"{agent.name}对{target.name}说了{dialogue or '话'}",
            )

        # ④ NPC→Item: interact_narrative LLM
        narrative = story or f"{agent.name}对{target.name}做了交互"
        action_text = decision.get("action", "")
        narrative, llm2_prompt, llm2_output = await self._resolve_npc_item(agent, target, action_text, story, narrative, world)

        # ⑤ Gate transfer
        self._handle_gate_transfer(agent, target_inter, world)

        return ActionResult(
            target_id=target.id,
            caller_deltas=self_deltas,
            narrative=narrative,
            llm2_prompt=llm2_prompt,
            llm2_output=llm2_output,
        )

    def _write_agent_layers(self, agent, agent_layer, decision, dialogue, visual):
        """Write dialogue/visual/internal to agent's layers for observers to poll."""
        if dialogue and agent.has("auditory"):
            aud = agent.get("auditory")
            aud.properties["current_speech"] = dialogue
            aud.properties["speech_ts"] = time.time()
            if agent_layer:
                agent_layer._conversation_buffer.append({"speaker": agent.name, "text": dialogue, "ts": time.time()})
                if len(agent_layer._conversation_buffer) > 8:
                    agent_layer._conversation_buffer.pop(0)
        if visual and agent.has("visual"):
            agent.get("visual").properties["expression"] = visual
            agent.get("visual").properties["expression_ts"] = time.time()
        if agent_layer and decision.get("remember"):
            mem = decision.get("story", "") or decision.get("action", "")
            if mem:
                agent_layer.memory.record(mem)

    async def _resolve_npc_item(self, agent, target, action_text, story, fallback_narrative, world=None):
        """NPC→Item: call LLM for narrative + deltas.
        Returns (narrative, llm2_prompt, llm2_output).
        """
        narrative = fallback_narrative
        llm2_prompt, llm2_output = "", ""
        target_inter = target.get("interaction")
        if not self.llm or not self.assembler:
            return narrative, llm2_prompt, llm2_output
        try:
            agent_inter = agent.get("interaction").private_attrs if agent.has("interaction") else {}
            context = {
                "action_description": action_text or story or "",
                "caller_name": agent.name,
                "caller_personality": agent.get("agent").personality if agent.has("agent") else "",
                "caller_state": json.dumps(agent_inter, ensure_ascii=False),
                "caller_id": agent.id,
                "target_name": target.name,
                "target_description": target_inter.properties.get("description", "") if target_inter.properties else getattr(target, 'describe', '') or target.name,
                "target_hidden": json.dumps(target_inter.hidden, ensure_ascii=False) if target_inter.hidden else "",
                "target_context": "",
                "target_id": target.id,
            }
            llm2_prompt = self.assembler.assemble("interact_narrative", context)
            system = self.assembler.get_system_prompt("interact_narrative")
            schema = self.assembler.get_output_schema("interact_narrative")
            temp = self.assembler.get_temperature("interact_narrative")
            raw = await self.llm.chat(system=system, messages=[{"role":"user","content":llm2_prompt}],
                                       temperature=temp, response_format=schema)
            llm2_output = raw
            from agent.brain import _parse_llm_json
            data = _parse_llm_json(raw, "interact_narrative")
            narrative = data.get("narrative", narrative)
            deltas = data.get("deltas", {})
            extra = deltas.get(agent.id, {})
            if extra:
                self._apply_deltas(agent, extra)
            target_changes = data.get("target_changes", {})
            if target_changes and target_inter and not target_inter.readonly:
                world.update_entity(target.id, target_changes)
        except Exception as e:
            from core.error_collector import errors
            errors.log_exception("interaction._resolve_npc_item", e,
                                 f"{agent.name}→{target.name}")
        if agent.has("agent") and narrative:
            agent.get("agent")._pending_narrative = narrative
        return narrative, llm2_prompt, llm2_output

    def _handle_gate_transfer(self, agent, target_inter, world):
        """If target interaction defines a gate, transfer the agent to the target zone."""
        gate = target_inter.gate if target_inter else None
        if gate and hasattr(world, 'lifecycle'):
            world.lifecycle.transfer_zone(agent, gate["to_zone"],
                                           list(gate.get("to_pos", agent.pos)))

    def _apply_deltas(self, entity, deltas: dict) -> None:
        if not entity.has("interaction"):
            return
        # Apply with built-in clamping (InteractionLayer handles bounds)
        entity.get("interaction").apply_deltas(deltas)
        # Post-apply verification (diagnostic only)
        from core.verification import verify
        inter = entity.get("interaction")
        issues = verify(entity, deltas, inter.currency_key,
                        inter.drive_min, inter.drive_max)
        if issues:
            logger.warning(f"Verification flag for {entity.name}: {'; '.join(issues)}")
