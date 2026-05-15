"""Agent loop — production run_agent(). All config injected."""
import time
import asyncio
from core.kl_divergence import total_kl, snapshot_p
from systems.interaction import check_observing


async def run_agent(agent, world, brain, assembler, systems,
                    runtime: float, *, trace_fn=None, cfg: dict = None):
    if cfg is None:
        cfg = {}
    name = agent.name
    al = agent.get("agent")
    end = time.time() + runtime
    poll = cfg.get("poll_interval", 0.3)
    thresholds = cfg.get("thresholds", [30, 60, 80])
    coin_eps = cfg.get("coin_epsilon", 5)
    stale_to = cfg.get("stale_timeout", 30)
    currency = cfg.get("currency", "coins")
    sim_text = cfg.get("text", {})
    labels = cfg.get("labels", {})
    intent_ttl = cfg.get("intent_ttl", 30)
    patience_default = cfg.get("default_patience", 5)
    speech_window = cfg.get("speech_window", 30)
    dup_mask = cfg.get("dup_mask", [])
    dup_prefix_len = cfg.get("dup_prefix_len", 40)

    while time.time() < end:
        try:
            elapsed = max(world.clock.now() - agent.last_action_time, 0)
            systems["decay"].tick(agent, elapsed)
            systems["sensory"].update(agent, world.entities, world,
                                       speech_window=speech_window)
            systems["interaction"].update_sensory(agent, world.entities)
            world.prune_events()
            al.inbox.drain()

            sensory = al.sensory

            if agent.expects_reply:
                result = check_observing(agent, sensory, sim_text)
                if result:
                    continue

            drives = al.drives
            coins = round(float(agent.get("interaction").private_attrs.get(currency, 0)))
            kl_text = total_kl(agent, sensory, drives, currency, sim_text,
                                thresholds, coin_eps, stale_to)

            if not kl_text:
                await asyncio.sleep(poll)
                continue

            latest_mem = al.memory.latest()
            if latest_mem and latest_mem.get("text", "").startswith(labels.get("intent_prefix", "INTENT:")):
                mem_age = time.time() - latest_mem["ts"]
                if mem_age < intent_ttl:
                    prefix = labels.get("intent_prefix", "INTENT:")
                    intent_action = latest_mem["text"][len(prefix):].strip()
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
                            snapshot_p(agent, sensory, drives, currency, sim_text,
                                       thresholds, coin_eps)
                            await asyncio.sleep(poll)
                            continue
                    latest_mem["text"] = labels.get("intent_stale", "STALE: ") + intent_action

            ctx = {
                "round": 0, "name": agent.name, "personality": al.personality,
                "drives_table": al.drives.to_prompt_table(labels),
                "zone_name": world.zones.get(agent.zone, {}).get("name", ""),
                "zone_width": world.zones.get(agent.zone, {}).get("width", 10),
                "zone_height": world.zones.get(agent.zone, {}).get("height", 10),
                "pos_x": agent.pos[0], "pos_y": agent.pos[1],
                "interactable_text": sensory.to_prompt("visual", labels),
                "visible_text": "",
                "memory_text": al.memory.to_prompt_text(
                    cfg.get("memory_prompt_count", 5), labels),
                "messages_text": "",
                "hearing_text": sensory.to_prompt("auditory", labels),
                "kl_text": kl_text,
            }

            prompt1 = assembler.assemble("agent_decision", ctx)

            if agent._write_pending:
                agent._write_pending = False
                snapshot_p(agent, sensory, drives, currency, sim_text,
                           thresholds, coin_eps)
                await asyncio.sleep(poll)
                continue

            decision = await brain.decide(ctx)

            # Duplication check: mute channels that repeat previous output
            if dup_mask:
                from core.duplication import check as dup_check
                allowed = dup_check(agent, decision, dup_mask, dup_prefix_len)
                if not all(allowed.values()):
                    snapshot_p(agent, sensory, drives, currency, sim_text,
                               thresholds, coin_eps)
                    await asyncio.sleep(poll)
                    continue
                for ch in dup_mask:
                    if not allowed.get(ch, True):
                        decision[ch] = ""

            move_to = decision.get("move_to")
            action_text = decision.get("action")

            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                systems["sensory"].update(agent, world.entities, world,
                                           speech_window=speech_window)
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
                                "agent": name, "target": target.name,
                                "target_id": target.id,
                                "action_text": action_text,
                                "action_name": action_name,
                                "llm1_output": decision,
                                "llm1_prompt": prompt1,
                                "result_narrative": result.narrative if result else "",
                                "result_caller_deltas": result.caller_deltas if result else {},
                                "result_target_deltas": result.target_deltas if result else {},
                                "zone": agent.zone, "pos": list(agent.pos),
                                "drives": {k:round(v,1) for k,v in drives.attrs.items()},
                                "coins": coins, "kl_text": kl_text,
                            })
                        if decision.get("expects_reply") and target.has("agent"):
                            agent.expects_reply = True
                            agent.observing_target = target.id
                            agent.observing_since = time.time()
                            agent.observing_timeout = decision.get("patience", patience_default)
                elif target and not systems["interaction"].can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world,
                                               speech_window=speech_window)
                    systems["interaction"].update_sensory(agent, world.entities)
                    intent_prefix = labels.get("intent_prefix", "INTENT:")
                    al.memory.record(f"{intent_prefix}{action_text}", ts=time.time())

            snapshot_p(agent, sensory, drives, currency, sim_text,
                       thresholds, coin_eps)
            await asyncio.sleep(0)

        except Exception as e:
            import sys
            print(f"  [{name}] error: {e}", file=sys.stderr, flush=True)
            await asyncio.sleep(3)
