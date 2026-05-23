"""Agent loop — phase-based pipeline. All config injected via LoopConfig.

Phase order: sense → KL gate → decide → act
Each phase may skip the remainder via continue.
"""
import time
import asyncio
from dataclasses import dataclass, field
from core.delta_gate import total_delta, snapshot_p


@dataclass
class LoopConfig:
    """Structured config for agent loop — type-safe, self-documenting."""
    poll_interval: float = 0.3
    thresholds: list = field(default_factory=lambda: [30, 60, 80])
    coin_epsilon: float = 5
    stale_timeout: float = 30
    currency: str = "coins"
    text: dict = field(default_factory=dict)
    labels: dict = field(default_factory=dict)
    default_patience: int = 5
    memory_prompt_count: int = 5


# ── helpers ──

def _make_trace(agent_name, target_name, target_id, action_text,
                zone, pos, drives, coins, delta_text, sim_time,
                *, llm1_output=None, llm1_prompt=None, result=None,
                note=None, thread_completed: bool = False,
                intent: str = "") -> dict:
    """Build a trace dict for a single agent action.
    llm1_output and llm1_prompt omitted for intent-executed actions.
    """
    trace = {
        "agent": agent_name, "target": target_name, "target_id": target_id,
        "action_text": action_text, "zone": zone, "pos": list(pos),
        "drives": {k: round(float(v), 1) for k, v in drives.attrs.items()},
        "coins": coins, "delta_text": delta_text, "sim_time": sim_time,
        "thread_completed": thread_completed,
        "intent": intent,
    }
    if result:
        trace["result_narrative"] = result.narrative
        trace["result_caller_deltas"] = result.caller_deltas
        if result.llm2_prompt:
            trace["llm2_prompt"] = result.llm2_prompt
        if result.llm2_output:
            trace["llm2_output"] = result.llm2_output
    if llm1_output:
        trace["llm1_output"] = llm1_output
    if llm1_prompt:
        trace["llm1_prompt"] = llm1_prompt
    if note:
        trace["note"] = note
    return trace


def _build_sensory_text(sensory, labels: dict) -> str:
    """Render all sensory channels from YAML sensory_prompts template."""
    sp = labels.get("sensory_prompts", {})
    parts = [t for ch, cfg in sp.items() if (t := sensory.to_prompt(ch, cfg))]
    return "\n\n".join(parts)


def _build_decision_ctx(agent, al, world, sensory, labels, cfg, delta_text) -> dict:
    """Construct the LLM decision context dict."""
    ctx = {
        "main_thread": al.main_thread,
        "name": agent.name, "personality": al.personality,
        "drives_table": al.drives.to_prompt(),
        "zone_name": world.zones.get(agent.zone, {}).get("name", ""),
        "zone_width": world.zones.get(agent.zone, {}).get("width", 10),
        "zone_height": world.zones.get(agent.zone, {}).get("height", 10),
        "pos_x": agent.pos[0], "pos_y": agent.pos[1],
        "sensory_text": _build_sensory_text(sensory, labels),
        "memory_text": al.memory.to_prompt_text(cfg.memory_prompt_count, labels),
        "delta_text": delta_text,
        "state_description": _build_state_text(al),
        "conversation_text": _build_conversation_text(al),
        "item_narrative": al._pending_narrative,
        "gate_text": _build_gate_text(agent, world),
    }
    al._pending_narrative = ""
    return ctx


def _build_gate_text(agent, world) -> str:
    """Report nearby gate entities as pure fact — no judgment about crossing."""
    zone_entities = [e for e in world.entities.values() if e.zone == agent.zone]
    gates = []
    for e in zone_entities:
        inter = e.get("interaction") if e.has("interaction") else None
        if inter and inter.gate:
            dist = agent.distance_to(e)
            to_zone_name = world.zones.get(inter.gate.get("to_zone", ""), {}).get("name", "")
            gates.append(f"{e.name} ({dist}格) → {to_zone_name}")
    return "\n".join(gates) if gates else ""


def _build_state_text(al) -> str:
    """Render factual state description from agent memory and conversation tracking.
    Pure facts — no cognitive judgment. Engine says what happened, not what to do.
    """
    parts = []
    latest = al.memory.latest()
    if latest:
        parts.append(latest.get("text", ""))
    if al._last_target_name:
        line = f"上一轮你与{al._last_target_name}交谈"
        if al._last_expects_reply:
            line += "，你当时期待对方回应"
        parts.append(line)
    return "；".join(parts) if parts else ""


def _build_conversation_text(al) -> str:
    """Render recent conversation as bare facts — who said what.
    Engine reports dialogue, LLM judges relevance.
    """
    buf = al._conversation_buffer[-5:]  # most recent 5 utterances
    if not buf:
        return ""
    lines = []
    for e in buf:
        ts = int(time.time() - e["ts"])
        lines.append(f"[{ts}s前] {e['speaker']}: {e['text']}")
    return "\n".join(lines)


def _build_traits_text(al, loader) -> str:
    """Render trait templates selected for this agent."""
    all_traits = loader.data.get("traits", {})
    parts = []
    for t in al.traits:
        if t in all_traits:
            parts.append(all_traits[t]["template"])
    return "\n\n".join(parts)


def _build_intent_context(al) -> dict:
    """Build intent feedback ctx — engine reports facts, LLM judges outcome."""
    if not al._last_intent:
        return {}
    since = [e for e in al._conversation_buffer if e["ts"] > al._last_action_ts]
    conv_lines = [f"- {e['speaker']}: {e['text']}" for e in since[-5:] if e.get("text")]
    drives_now = al.drives.attrs
    old = al._last_action_drives
    delta_lines = []
    for k in sorted(set(old) | set(drives_now)):
        d = round(float(drives_now.get(k, 0)) - float(old.get(k, 0)), 1)
        if d != 0:
            dir_sym = "↑" if d > 0 else "↓"
            delta_lines.append(f"- {k} {dir_sym}{abs(d)}")
    return {
        "last_intent": al._last_intent,
        "last_target": al._last_intent_target,
        "conversation_since_last_action": "\n".join(conv_lines) or "（无新对话）",
        "drive_delta_since_last_action": "\n".join(delta_lines) or "（无变化）",
    }


def _build_drive_boundaries_text(attr_cfg: dict) -> str:
    """Render drive boundary values only (0 and 100) as factual reference."""
    lines = []
    for attr, cfg in sorted(attr_cfg.items()):
        desc = cfg.get("description", "")
        lo = desc.split("0=", 1)[-1].split("。")[0].split("，")[0] if "0=" in desc else ""
        hi = desc.split("100=", 1)[-1].split("。")[0].split("，")[0] if "100=" in desc else ""
        parts = [f"{attr}: {lo}"] if lo else [attr]
        if hi:
            parts.append(f"100={hi}")
        lines.append(" → ".join(parts) if len(parts) > 1 else parts[0])
    return "\n".join(lines)


# ── main loop ──

async def run_agent(agent, world, brain, assembler, systems,
                    runtime: float, *, trace_fn=None, cfg: LoopConfig = None,
                    director=None, dashboard_emit=None):
    if cfg is None:
        cfg = LoopConfig()
    name = agent.name
    al = agent.get("agent")
    end = time.time() + runtime
    interaction = systems["interaction"]
    labels = cfg.labels

    prompt1 = None  # scoped for trace_fn access across Phase 3→4
    while time.time() < end:
        try:
            # ═══════════════════════════════════════════
            #  FREEZE CHECK
            # ═══════════════════════════════════════════
            if director and director.frozen:
                await asyncio.sleep(cfg.poll_interval)
                continue

            # ═══════════════════════════════════════════
            #  PHASE 1: SENSE
            # ═══════════════════════════════════════════
            elapsed = max(world.clock.now() - agent.last_action_time, 0)
            systems["decay"].tick(agent, elapsed)
            systems["sensory"].update(agent, world.entities, world,
                                       channel_configs=labels.get("sensory_prompts"))
            sensory = al.sensory
            if dashboard_emit:
                vis = sensory.channels.get("visual", {})
                aud = sensory.channels.get("auditory", {})
                dashboard_emit({"agent": name, "zone": agent.zone,
                                "phase": "sensory",
                                "visual": [{"name": r.name, "distance": r.distance, "look": r.data.get("look", "")}
                                           for r in vis.values()],
                                "auditory": [{"name": r.name, "speech": r.data.get("current_speech", "")}
                                            for r in aud.values()]})

            # Controlled agent: execute external order or sleep
            if director and director.is_controlled(agent.id):
                decision = director.pending(agent.id)
                if decision:
                    pass  # go to Phase 4 to execute
                else:
                    await asyncio.sleep(cfg.poll_interval)
                    continue

            # ═══════════════════════════════════════════
            #  PHASE 2: KL GATE
            # ═══════════════════════════════════════════
            drives = al.drives
            coins = round(float(agent.get("interaction").private_attrs.get(cfg.currency, 0)))
            delta_text = total_delta(al, sensory, drives, cfg.currency, cfg.text,
                                 cfg.thresholds, cfg.coin_epsilon, cfg.stale_timeout)

            if not delta_text:
                await asyncio.sleep(cfg.poll_interval)
                continue

            # ═══════════════════════════════════════════
            #  PHASE 3: DECIDE
            # ═══════════════════════════════════════════
            # Action pacing: skip if still executing prior action
            if time.time() < al._action_complete_at:
                snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                           cfg.thresholds, cfg.coin_epsilon)
                await asyncio.sleep(cfg.poll_interval)
                continue

            # Write-pending lock: skip one cycle after interacting
            # Ensures sensory consistency — agent's own action absorbed before next decision
            if al._write_pending:
                al._write_pending = False
                snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                           cfg.thresholds, cfg.coin_epsilon)
                await asyncio.sleep(cfg.poll_interval)
                continue

            ctx = _build_decision_ctx(agent, al, world, sensory, labels, cfg, delta_text)
            # Inject slot-group-controlled context (not in base builder)
            ctx["traits_text"] = _build_traits_text(al, assembler.loader)
            ctx["drive_boundaries"] = _build_drive_boundaries_text(al.drives.attr_cfg)
            ctx.update(_build_intent_context(al))
            prompt1 = assembler.assemble("agent_decision", ctx) if trace_fn else None

            decision = await brain.decide(ctx, template_name=al.template or "agent_decision",
                                           provider=al.llm_provider, slot_mask=al.slot_mask)
            if dashboard_emit:
                dashboard_emit({"agent": name, "zone": agent.zone,
                                "phase": "decision",
                                "intent": decision.get("intent", ""),
                                "thinking": decision.get("thinking", ""),
                                "main_thread": decision.get("main_thread", ""),
                                "internal": decision.get("internal", "")})
            if decision.get("main_thread"):
                al.main_thread = decision["main_thread"]

            # ═══════════════════════════════════════════
            #  PHASE 4: ACT
            # ═══════════════════════════════════════════
            target_name = decision.get("target_name")
            action_text = decision.get("action")
            if target_name and action_text:
                target = interaction.find_entity_by_name(
                    agent.zone, target_name, world.entities,
                    exclude_id=agent.id)
                if target and interaction.can_interact(agent, target):
                    result = await interaction.interact(
                        agent, target, decision, world)
                    agent.last_action_time = world.clock.now()
                    al._last_target_name = target.name
                    al._last_expects_reply = bool(decision.get("expects_reply"))
                    al._last_intent = decision.get("intent", "")
                    al._last_intent_target = target.name
                    al._last_action_ts = time.time()
                    al._last_action_drives = {k: round(float(v), 1) for k, v in drives.attrs.items()}
                    al._action_complete_at = time.time() + max(0.5, decision.get("duration", 3.0))
                    if dashboard_emit:
                        dashboard_emit({"agent": name, "zone": agent.zone,
                                        "phase": "action",
                                        "action_text": action_text,
                                        "dialogue": decision.get("dialogue", ""),
                                        "story": decision.get("story", ""),
                                        "target_name": target_name,
                                        "drives": {k: round(float(v), 1) for k, v in drives.attrs.items()},
                                        "coins": coins,
                                        "intent": decision.get("intent", ""),
                                        "main_thread": decision.get("main_thread", ""),
                                        "thread_completed": decision.get("thread_completed", False)})
                    if trace_fn:
                        trace_fn(_make_trace(
                            name, target.name, target.id, action_text,
                            agent.zone, agent.pos, drives, coins,
                            delta_text, world.clock.now(),
                            llm1_output=decision, result=result,
                            llm1_prompt=prompt1,
                            thread_completed=decision.get("thread_completed", False),
                            intent=decision.get("intent", "")))
                elif target and not interaction.can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world,
                                               channel_configs=labels.get("sensory_prompts"))
            elif action_text and not target_name:
                # No target specified — try action-only move
                target = interaction.find_entity_at(
                    agent.zone, agent.pos, action_text, world.entities,
                    exclude_id=agent.id)
                if target and not interaction.can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world,
                                               channel_configs=labels.get("sensory_prompts"))

            snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                       cfg.thresholds, cfg.coin_epsilon)
            await asyncio.sleep(0)

        except Exception as e:
            from core.error_collector import errors
            errors.log_exception(f"loop.{name}", e)
            await asyncio.sleep(3)
