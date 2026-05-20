"""Agent loop — phase-based pipeline. All config injected via LoopConfig.

Phase order: sense → KL gate → decide → act
Each phase may skip the remainder via continue.
"""
import time
import asyncio
from dataclasses import dataclass, field
from core.kl_divergence import total_kl, snapshot_p


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
                zone, pos, drives, coins, kl_text, sim_time,
                *, llm1_output=None, llm1_prompt=None, result=None,
                note=None) -> dict:
    """Build a trace dict for a single agent action.
    llm1_output and llm1_prompt omitted for intent-executed actions.
    """
    trace = {
        "agent": agent_name, "target": target_name, "target_id": target_id,
        "action_text": action_text, "zone": zone, "pos": list(pos),
        "drives": {k: round(float(v), 1) for k, v in drives.attrs.items()},
        "coins": coins, "kl_text": kl_text, "sim_time": sim_time,
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


def _speech_window(cfg) -> int:
    """Read speech window from YAML sensory_prompts, not engine code."""
    sp = cfg.labels.get("sensory_prompts", {})
    return sp.get("auditory", {}).get("window_seconds", 30)


def _build_sensory_text(sensory, labels: dict) -> str:
    """Render all sensory channels from YAML sensory_prompts template."""
    sp = labels.get("sensory_prompts", {})
    parts = [t for ch, cfg in sp.items() if (t := sensory.to_prompt(ch, cfg))]
    return "\n\n".join(parts)


def _build_decision_ctx(agent, al, world, sensory, labels, cfg, kl_text) -> dict:
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
        "kl_text": kl_text,
        "state_description": _build_state_text(al),
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
        parts.append(f"上一轮交互对象: {al._last_target_name}")
    return "；".join(parts) if parts else ""


# ── main loop ──

async def run_agent(agent, world, brain, assembler, systems,
                    runtime: float, *, trace_fn=None, cfg: LoopConfig = None,
                    director=None):
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
                                       speech_window=_speech_window(cfg))
            sensory = al.sensory

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
            kl_text = total_kl(al, sensory, drives, cfg.currency, cfg.text,
                                cfg.thresholds, cfg.coin_epsilon, cfg.stale_timeout)

            if not kl_text:
                await asyncio.sleep(cfg.poll_interval)
                continue

            # ═══════════════════════════════════════════
            #  PHASE 3: DECIDE
            # ═══════════════════════════════════════════
            # Write-pending lock: skip one cycle after interacting
            if al._write_pending:
                al._write_pending = False
                snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                           cfg.thresholds, cfg.coin_epsilon)
                await asyncio.sleep(cfg.poll_interval)
                continue

            ctx = _build_decision_ctx(agent, al, world, sensory, labels, cfg, kl_text)
            prompt1 = assembler.assemble("agent_decision", ctx) if trace_fn else None

            decision = await brain.decide(ctx, template_name=al.template or "agent_decision",
                                           provider=al.llm_provider)
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
                    if trace_fn:
                        trace_fn(_make_trace(
                            name, target.name, target.id, action_text,
                            agent.zone, agent.pos, drives, coins,
                            kl_text, world.clock.now(),
                            llm1_output=decision, result=result,
                            llm1_prompt=prompt1))
                elif target and not interaction.can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world,
                                               speech_window=_speech_window(cfg))
            elif action_text and not target_name:
                # No target specified — try action-only move
                target = interaction.find_entity_at(
                    agent.zone, agent.pos, action_text, world.entities,
                    exclude_id=agent.id)
                if target and not interaction.can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world,
                                               speech_window=_speech_window(cfg))

            snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                       cfg.thresholds, cfg.coin_epsilon)
            await asyncio.sleep(0)

        except Exception as e:
            from core.error_collector import errors
            errors.log_exception(f"loop.{name}", e)
            await asyncio.sleep(3)
