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
    intent_ttl: int = 30
    default_patience: int = 5
    speech_window: int = 30
    memory_prompt_count: int = 5


async def run_agent(agent, world, brain, assembler, systems,
                    runtime: float, *, trace_fn=None, cfg: LoopConfig = None):
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
            #  PHASE 1: SENSE
            # ═══════════════════════════════════════════
            elapsed = max(world.clock.now() - agent.last_action_time, 0)
            systems["decay"].tick(agent, elapsed)
            systems["sensory"].update(agent, world.entities, world,
                                       speech_window=cfg.speech_window)
            sensory = al.sensory

            # ═══════════════════════════════════════════
            #  PHASE 2: KL GATE — only act if something changed
            # ═══════════════════════════════════════════
            drives = al.drives
            coins = round(float(agent.get("interaction").private_attrs.get(cfg.currency, 0)))
            kl_text = total_kl(al, sensory, drives, cfg.currency, cfg.text,
                                cfg.thresholds, cfg.coin_epsilon, cfg.stale_timeout)

            if not kl_text:
                await asyncio.sleep(cfg.poll_interval)
                continue

            # ═══════════════════════════════════════════
            #  PHASE 2b: INTENT — execute stale intent if fresh
            # ═══════════════════════════════════════════
            latest_mem = al.memory.latest()
            intent_prefix = labels.get("intent_prefix", "INTENT:")
            if latest_mem and latest_mem.get("text", "").startswith(intent_prefix):
                intent_action = latest_mem["text"][len(intent_prefix):].strip()
                mem_age = time.time() - latest_mem["ts"]
                if mem_age < cfg.intent_ttl:
                    intent_target = interaction.find_entity_at(
                        agent.zone, agent.pos, intent_action, world.entities,
                        exclude_id=agent.id)
                    if intent_target and interaction.can_interact(agent, intent_target):
                        result = await interaction.interact(
                            agent, intent_target, {}, world)
                        agent.last_action_time = world.clock.now()
                        latest_mem["text"] += " ✓"
                        if trace_fn:
                            trace_fn({
                                "agent": name, "target": intent_target.name,
                                "action_text": intent_action, "note": "from_intent",
                                "result_narrative": result.narrative if result else "",
                                "zone": agent.zone, "pos": list(agent.pos),
                                "drives": {k: round(v, 1) for k, v in drives.attrs.items()},
                                "coins": coins, "kl_text": kl_text,
                            })
                        snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                                   cfg.thresholds, cfg.coin_epsilon)
                        await asyncio.sleep(cfg.poll_interval)
                        continue
                latest_mem["text"] = labels.get("intent_stale", "STALE: ") + intent_action

            # ═══════════════════════════════════════════
            #  PHASE 3: DECIDE — LLM decision
            # ═══════════════════════════════════════════

            # Drain inbox only now — we are actually going to decide
            inbox_text = al.inbox.to_prompt_text()
            al.inbox.drain()

            # Render all sensory channels from YAML
            sp = labels.get("sensory_prompts", {})
            sensory_parts = []
            for ch_name, ch_cfg in sp.items():
                t = sensory.to_prompt(ch_name, ch_cfg)
                if t: sensory_parts.append(t)

            ctx = {
                "name": agent.name, "personality": al.personality,
                "drives_table": al.drives.to_prompt_table(labels),
                "zone_name": world.zones.get(agent.zone, {}).get("name", ""),
                "zone_width": world.zones.get(agent.zone, {}).get("width", 10),
                "zone_height": world.zones.get(agent.zone, {}).get("height", 10),
                "pos_x": agent.pos[0], "pos_y": agent.pos[1],
                "sensory_text": "\n\n".join(sensory_parts),
                "messages_text": inbox_text,
                "memory_text": al.memory.to_prompt_text(cfg.memory_prompt_count, labels),
                "kl_text": kl_text,
            }

            prompt1 = assembler.assemble("agent_decision", ctx)

            # Write-pending lock: skip one cycle after interacting
            if al._write_pending:
                al._write_pending = False
                snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                           cfg.thresholds, cfg.coin_epsilon)
                await asyncio.sleep(cfg.poll_interval)
                continue

            decision = await brain.decide(ctx)

            # ═══════════════════════════════════════════
            #  PHASE 4: ACT — move / interact
            # ═══════════════════════════════════════════
            move_to = decision.get("move_to")
            action_text = decision.get("action")

            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                systems["sensory"].update(agent, world.entities, world,
                                           speech_window=cfg.speech_window)

            if action_text:
                target = interaction.find_entity_at(
                    agent.zone, agent.pos, action_text, world.entities,
                    exclude_id=agent.id)
                if target and interaction.can_interact(agent, target):
                    result = await interaction.interact(
                        agent, target, decision, world)
                    agent.last_action_time = world.clock.now()
                    if trace_fn:
                        trace_fn({
                            "agent": name, "target": target.name,
                            "target_id": target.id,
                            "action_text": action_text,
                            "llm1_output": decision,
                            "llm1_prompt": prompt1,
                            "result_narrative": result.narrative if result else "",
                            "result_caller_deltas": result.caller_deltas if result else {},
                            "result_target_deltas": result.target_deltas if result else {},
                            "zone": agent.zone, "pos": list(agent.pos),
                            "drives": {k: round(v, 1) for k, v in drives.attrs.items()},
                            "coins": coins, "kl_text": kl_text,
                        })
                elif target and not interaction.can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world,
                                               speech_window=cfg.speech_window)
                    al.memory.record(f"{intent_prefix}{action_text}", ts=time.time())

            snapshot_p(al, sensory, drives, cfg.currency, cfg.text,
                       cfg.thresholds, cfg.coin_epsilon)
            await asyncio.sleep(0)

        except Exception as e:
            import sys
            print(f"  [{name}] error: {e}", file=sys.stderr, flush=True)
            await asyncio.sleep(3)
