"""InteractionSystem — 统一交互模型
interact() 是唯一入口。NPC→NPC: 纯同步写层。NPC→Item: +1 LLM。
check_observing() — observing 闭环检测
"""
import json
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def check_observing(agent, sensory, text: dict = None) -> str | None:
    """Observing 闭环检测。返回结束原因或 None (继续等待)。"""
    if not text:
        text = {"observed_replied": '{name}说："{speech}"',
                "observed_left": "{name}走远了",
                "observed_no_reply": "{name}没有回应我"}
    if not agent.expects_reply or not agent.observing_target:
        return None
    heard = sensory.hearing.get(agent.observing_target)
    if heard and (heard.auditory_data.get("current_speech", "") or heard.auditory_data.get("sound", "")):
        speech = heard.auditory_data.get("current_speech", "") or heard.auditory_data.get("sound", "")
        agent.get("agent").memory.record(
            text["observed_replied"].format(name=heard.name, speech=speech))
        agent.expects_reply = False
        agent.observing_target = ""
        return "replied"
    seen = sensory.vision.get(agent.observing_target)
    if not seen or seen.distance > agent.get("agent").view_radius * 0.8:
        agent.get("agent").memory.record(
            text["observed_left"].format(name=agent.observing_target))
        agent.expects_reply = False
        agent.observing_target = ""
        return "left"
    if time.time() - agent.observing_since > agent.observing_timeout:
        agent.get("agent").memory.record(
            text["observed_no_reply"].format(name=agent.observing_target))
        agent.expects_reply = False
        agent.observing_target = ""
        return "timeout"
    return None


@dataclass
class ActionResult:
    target_id: str = ""
    caller_deltas: dict = field(default_factory=dict)
    target_deltas: dict = field(default_factory=dict)
    narrative: str = ""


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

    def find_entity_at(self, zone: str, pos: list[int], action: str,
                       all_entities: dict, exclude_id: str = "") -> object | None:
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
        for d, e in candidates:
            desc = getattr(e, 'description', '') or ''
            for word in [e.name, *desc.split('.')[0].split(' ')]:
                if len(word) >= 2 and word in action:
                    return e
        best = candidates[0]
        if best[0] <= best[1].get("interaction").interaction_radius + 3:
            return best[1]
        return None

    def fuzzy_match_action(self, target, action_text: str) -> str | None:
        layer = target.get("interaction")
        if not layer or not layer.actions:
            return None
        for name in layer.actions:
            if name in action_text:
                return name
        for name in layer.actions:
            if len(name) <= 1:
                continue
            chars = set(name)
            overlap = sum(1 for c in chars if c in action_text)
            if overlap / len(chars) >= 0.5:
                return name
        for name in layer.actions:
            for ch in name:
                if ch in action_text:
                    return name
        if target.name in action_text and layer.actions:
            return list(layer.actions.keys())[0]
        if len(layer.actions) == 1:
            return list(layer.actions.keys())[0]
        return None

    def update_sensory(self, agent, all_entities: dict) -> None:
        sensory = agent.get("agent").sensory
        for eid, record in sensory.vision.items():
            if eid in all_entities:
                record.can_interact = self.can_interact(agent, all_entities[eid])

    # ═══════════ core: interact() ═══════════

    async def interact(self, agent, target, action_name: str,
                       decision: dict, world) -> ActionResult | None:
        """统一交互入口。同步写层，NPC→Item 加一次 LLM。"""
        action = target.get("interaction").actions.get(action_name)
        if not action:
            logger.warning(f"No action '{action_name}' on {target.name}")
            return None

        dialogue = decision.get("dialogue", "")
        visual = decision.get("visual", "")
        self_deltas = decision.get("self_deltas", {})
        story = decision.get("story", "")

        # ① Write agent's layers (observers poll)
        if dialogue and agent.has("auditory"):
            aud = agent.get("auditory")
            aud.properties["current_speech"] = dialogue
            aud.properties["speech_ts"] = time.time()
        if visual and agent.has("visual"):
            agent.get("visual").properties["expression"] = visual
            agent.get("visual").properties["expression_ts"] = time.time()
        if agent.has("agent"):
            agent.get("agent").memory.record(
                json.dumps(decision, ensure_ascii=False))

        # ② Apply self_deltas
        if self_deltas:
            self._apply_deltas(agent, self_deltas)

        agent._write_pending = True

        # ③ NPC→NPC: done
        if target.has("agent"):
            return ActionResult(
                target_id=target.id,
                caller_deltas=self_deltas,
                narrative=story or f"{agent.name}对{target.name}说了{dialogue or action_name}",
            )

        # ④ NPC→Item: interact_narrative LLM
        narrative = story or f"{agent.name}对{target.name}做了{action_name}"
        if self.llm and self.assembler:
            try:
                agent_inter = agent.get("interaction").private_attrs if agent.has("interaction") else {}
                context = {
                    "action_name": action_name,
                    "caller_name": agent.name,
                    "caller_personality": agent.get("agent").personality if agent.has("agent") else "",
                    "caller_state": json.dumps(agent_inter, ensure_ascii=False),
                    "caller_id": agent.id,
                    "target_name": target.name,
                    "target_description": getattr(target, 'description', '') or target.name,
                    "action_description": action.get("description", action_name),
                    "target_context": "",
                    "target_id": agent.id,
                }
                prompt = self.assembler.assemble("interact_narrative", context)
                system = self.assembler.get_system_prompt("interact_narrative")
                raw = await self.llm.chat(system=system, messages=[{"role":"user","content":prompt}])
                from agent.brain import extract_json
                data = json.loads(extract_json(raw))
                narrative = data.get("narrative", narrative)
                deltas = data.get("deltas", {})
                extra = deltas.get(agent.id, {})
                if extra:
                    self._apply_deltas(agent, extra)
            except Exception as e:
                import sys
                print(f"  [interact ERR] {agent.name}→{target.name}: {e}", file=sys.stderr, flush=True)

        if narrative:
            agent.get("agent").memory.record(narrative) if agent.has("agent") else None

        # ⑤ Gate transfer
        gate = action.get("gate")
        if gate and hasattr(world, 'lifecycle'):
            world.lifecycle.transfer_zone(agent, gate["to_zone"],
                                           list(gate.get("to_pos", agent.pos)))

        return ActionResult(
            target_id=target.id,
            caller_deltas=self_deltas,
            narrative=narrative,
        )

    def _apply_deltas(self, entity, deltas: dict) -> None:
        if not entity.has("interaction"):
            return
        entity.get("interaction").apply_deltas(deltas)
