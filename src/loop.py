"""Agent loop — phase-based pipeline. All config injected via LoopConfig.

Phase order: sense → KL gate → intent → decide → act
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
    intent_ttl: int = 30
    default_patience: int = 5
    speech_window: int = 30
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


def _build_decision_ctx(agent, al, world, sensory, labels, cfg, kl_text) -> dict:
    """Construct the LLM decision context dict."""
    return {
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
    }


async def _handle_intent(agent, al, world, interaction, labels, cfg,
                   drives, coins, kl_text, trace_fn) -> bool:
    """Execute stale intent if fresh. Returns True if intent was consumed."""
    latest_mem = al.memory.latest()
    intent_prefix = labels.get("intent_prefix", "INTENT:")
    if not (latest_mem and latest_mem.get("text", "").startswith(intent_prefix)):
        return False

    intent_action = latest_mem["text"][len(intent_prefix):].strip()
    mem_age = time.time() - latest_mem["ts"]
    if mem_age >= cfg.intent_ttl:
        latest_mem["text"] = labels.get("intent_stale", "STALE: ") + intent_action
        return False

    intent_target = interaction.find_entity_at(
        agent.zone, agent.pos, intent_action, world.entities, exclude_id=agent.id)
    if not intent_target or not interaction.can_interact(agent, intent_target):
        return False

    result = await interaction.interact(agent, intent_target, {}, world)
    agent.last_action_time = world.clock.now()
    latest_mem["text"] = labels.get("intent_done", "DONE: ") + intent_action

    if trace_fn:
        trace_fn(_make_trace(agent.name, intent_target.name, intent_target.id,
                             intent_action, agent.zone, agent.pos, drives, coins,
                             kl_text, world.clock.now(),
                             result=result, note="from_intent"))
    return True


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
                                       speech_window=cfg.speech_window)
            sensory = al.sensory

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
            #  PHASE 2b: INTENT
            # ═══════════════════════════════════════════
            if await _handle_intent(agent, al, world, interaction, labels, cfg,
                                    drives, coins, kl_text, trace_fn):
                snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                           cfg.thresholds, cfg.coin_epsilon)
                await asyncio.sleep(cfg.poll_interval)
                continue

            # ═══════════════════════════════════════════
            #  PHASE 3: DECIDE
            # ═══════════════════════════════════════════
            if director and director.is_controlled(agent.id):
                decision = director.pending(agent.id)
                if not decision:
                    snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                               cfg.thresholds, cfg.coin_epsilon)
                    await asyncio.sleep(cfg.poll_interval)
                    continue
                # decision found: skip ctx, skip LLM, go to Phase 4
            else:
                # Write-pending lock: skip one cycle after interacting
                if al._write_pending:
                    al._write_pending = False
                    snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                               cfg.thresholds, cfg.coin_epsilon)
                    await asyncio.sleep(cfg.poll_interval)
                    continue

                ctx = _build_decision_ctx(agent, al, world, sensory, labels, cfg, kl_text)
                prompt1 = assembler.assemble("agent_decision", ctx) if trace_fn else None

                decision = await brain.decide(ctx)
                if decision.get("main_thread"):
                    al.main_thread = decision["main_thread"]

            # ═══════════════════════════════════════════
            #  PHASE 4: ACT
            # ═══════════════════════════════════════════
            action_text = decision.get("action")
            if action_text:
                target = interaction.find_entity_at(
                    agent.zone, agent.pos, action_text, world.entities,
                    exclude_id=agent.id)
                if target and interaction.can_interact(agent, target):
                    result = await interaction.interact(
                        agent, target, decision, world)
                    agent.last_action_time = world.clock.now()
                    if trace_fn:
                        prompt = prompt1 if 'prompt1' in dir() else None
                        trace_fn(_make_trace(
                            name, target.name, target.id, action_text,
                            agent.zone, agent.pos, drives, coins,
                            kl_text, world.clock.now(),
                            llm1_output=decision, result=result,
                            llm1_prompt=prompt))
                elif target and not interaction.can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world,
                                               speech_window=cfg.speech_window)
                    al.memory.record(
                        f"{labels.get('intent_prefix', 'INTENT:')}{action_text}",
                        ts=time.time())

            snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                       cfg.thresholds, cfg.coin_epsilon)
            await asyncio.sleep(0)

        except Exception as e:
            import sys
            print(f"  [{name}] error: {e}", file=sys.stderr, flush=True)
            await asyncio.sleep(3)
