"""Agent loop — production run_agent().

Single entry for both main.py (production) and test harnesses.
Accepts optional trace_fn for debugging/validation.
"""
import time
import asyncio
from core.kl_divergence import total_kl, snapshot_p
from systems.interaction import check_observing


async def run_agent(agent, world, brain, assembler, systems,
                    runtime: float, *, trace_fn=None, kl_config=None):
    """Run one agent's observing + KL + decide + interact loop.

    Args:
        agent:       Entity with agent layer
        world:       World container
        brain:       Brain (LLM #1)
        assembler:   PromptAssembler
        systems:     {"sensory": ..., "interaction": ..., "decay": ...}
        runtime:     Max real-time seconds to run
        trace_fn:    Optional callback(trace_dict) for recording
        kl_config:   dict with keys: thresholds, coin_epsilon, stale_timeout
    """
    thresholds = kl_config.get("thresholds", [30, 60, 80]) if kl_config else [30, 60, 80]
    coin_epsilon = kl_config.get("coin_epsilon", 5) if kl_config else 5
    stale_timeout = kl_config.get("stale_timeout", 30) if kl_config else 30
    name = agent.name
    al = agent.get("agent")
    end = time.time() + runtime

    while time.time() < end:
        try:
            elapsed = max(world.clock.now() - agent.last_action_time, 0)
            systems["decay"].tick(agent, elapsed)
            systems["sensory"].update(agent, world.entities, world)
            systems["interaction"].update_sensory(agent, world.entities)
            world.prune_events()
            al.inbox.drain()

            sensory = al.sensory

            # ── Observing 闭环 ──
            if agent.expects_reply:
                result = check_observing(agent, sensory)
                if result:
                    continue

            # ── KL gate ──
            drives = al.drives
            coins = round(float(agent.get("interaction").private_attrs.get("coins", 0)))
            kl_text = total_kl(agent, sensory, drives, coins,
                                thresholds, coin_epsilon, stale_timeout)

            if not kl_text:
                await asyncio.sleep(0.3)
                continue

            # ── INTENT recovery ──
            latest_mem = al.memory.latest()
            if latest_mem and latest_mem.get("text", "").startswith("INTENT:"):
                mem_age = time.time() - latest_mem["ts"]
                if mem_age < 30:
                    intent_action = latest_mem["text"][len("INTENT:"):].strip()
                    intent_target = systems["interaction"].find_entity_at(
                        agent.zone, agent.pos, intent_action, world.entities,
                        exclude_id=agent.id)
                    if intent_target and systems["interaction"].can_interact(
                            agent, intent_target):
                        action_name = systems["interaction"].fuzzy_match_action(
                            intent_target, intent_action)
                        if action_name:
                            result = await systems["interaction"].interact(
                                agent, intent_target, action_name, {}, world)
                            agent.last_action_time = world.clock.now()
                            latest_mem["text"] += " ✓"
                            if trace_fn:
                                trace_fn({
                                    "agent": name, "target": intent_target.name,
                                    "action_text": intent_action, "note": "from_intent",
                                    "result_narrative": result.narrative if result else "",
                                    "zone": agent.zone, "pos": list(agent.pos),
                                    "drives": {k:round(v,1) for k,v in drives.attrs.items()},
                                    "coins": coins, "kl_text": kl_text,
                                })
                            snapshot_p(agent, sensory, drives, coins,
                                       thresholds, coin_epsilon)
                            await asyncio.sleep(0.3)
                            continue
                    latest_mem["text"] = f"STALE: {intent_action}"

            # ── Decide ──
            visible_text = ""
            if sensory.get_visible_only():
                visible_text = "\n".join(
                    f"id={r.entity_id}|{r.name}|dist={r.distance}"
                    for r in sensory.get_visible_only())

            ctx = {
                "round": 0, "name": agent.name, "personality": al.personality,
                "drives_table": al.drives.to_prompt_table(),
                "zone_name": world.zones.get(agent.zone, {}).get("name", ""),
                "zone_width": world.zones.get(agent.zone, {}).get("width", 10),
                "zone_height": world.zones.get(agent.zone, {}).get("height", 10),
                "pos_x": agent.pos[0], "pos_y": agent.pos[1],
                "interactable_text": sensory.to_prompt_vision(),
                "visible_text": visible_text,
                "memory_text": al.memory.to_prompt_text(5),
                "messages_text": "", "hearing_text": sensory.to_prompt_hearing(),
                "kl_text": kl_text,
            }

            prompt1 = assembler.assemble("agent_decision", ctx)
            decision = await brain.decide(ctx)
            move_to = decision.get("move_to")
            action_text = decision.get("action")

            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                systems["sensory"].update(agent, world.entities, world)
                systems["interaction"].update_sensory(agent, world.entities)

            if action_text:
                target = systems["interaction"].find_entity_at(
                    agent.zone, agent.pos, action_text, world.entities,
                    exclude_id=agent.id)
                if target and systems["interaction"].can_interact(agent, target):
                    action_name = systems["interaction"].fuzzy_match_action(
                        target, action_text)
                    if action_name:
                        result = await systems["interaction"].interact(
                            agent, target, action_name, decision, world)
                        agent.last_action_time = world.clock.now()

                        if trace_fn:
                            trace_fn({
                                "agent": name,
                                "target": target.name,
                                "target_id": target.id,
                                "action_text": action_text,
                                "action_name": action_name,
                                "llm1_output": decision,
                                "llm1_prompt": prompt1,
                                "result_narrative": result.narrative if result else "",
                                "result_caller_deltas": result.caller_deltas if result else {},
                                "result_target_deltas": result.target_deltas if result else {},
                                "zone": agent.zone,
                                "pos": list(agent.pos),
                                "drives": {k:round(v,1) for k,v in drives.attrs.items()},
                                "coins": coins,
                                "kl_text": kl_text,
                            })

                        if decision.get("expects_reply") and target.has("agent"):
                            agent.expects_reply = True
                            agent.observing_target = target.id
                            agent.observing_since = time.time()
                            agent.observing_timeout = decision.get("patience", 5)
                elif target and not systems["interaction"].can_interact(
                        agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world)
                    systems["interaction"].update_sensory(agent, world.entities)
                    al.memory.record(f"INTENT: {action_text}", ts=time.time())

            snapshot_p(agent, sensory, drives, coins)
            await asyncio.sleep(0)

        except Exception as e:
            import sys
            print(f"  [{name}] error: {e}", file=sys.stderr, flush=True)
            await asyncio.sleep(3)
