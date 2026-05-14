#!/usr/bin/env python3
"""E2E test — observing baseline + layered KL triggers."""
import sys, os, yaml, asyncio, uuid, json, time, logging
from datetime import datetime
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World; from agent.brain import Brain; from agent.drives import DriveSystem
from prompt.loader import PromptLoader; from prompt.assembler import PromptAssembler
from llm.client import LLMClient; from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem, check_observing; from systems.decay import DecaySystem
from core.kl_divergence import total_kl, snapshot_p

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "e2e_concurrent_trace.json")
LOG = os.path.join(BASE, "e2e_concurrent_log.jsonl")

EXTRA_NPCS = [
    {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[7,2],"personality":"老猎魔人","coins":200,"thirst":50,"social":30,"mood":55},
    {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],"personality":"女术士","coins":300,"thirst":35,"social":25,"mood":50},
    {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[7,2],"personality":"矮人商人","coins":500,"thirst":65,"social":60,"mood":70},
    {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],"personality":"年轻女术士","coins":150,"thirst":30,"social":15,"mood":60},
    {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],"personality":"猎魔人","coins":100,"thirst":70,"social":15,"mood":40},
]

test_start = time.time()
agent_traces: dict[str, list] = defaultdict(list)

def log(etype, **kw):
    e = {"ts": time.time()-test_start, "wall": datetime.now().isoformat(), "event": etype, **kw}
    with open(LOG, "a") as f: f.write(json.dumps(e, ensure_ascii=False)+"\n")


# ═══════════ Agent Loop ═══════════

async def run_agent(agent, world, brain, assembler, systems, runtime):
    name = agent.name; al = agent.get("agent")
    end = time.time() + runtime
    actions = 0

    while time.time() < end:
        try:
            elapsed = max(world.clock.now()-agent.last_action_time, 0)
            systems["decay"].tick(agent, elapsed)
            systems["sensory"].update(agent, world.entities, world)
            systems["interaction"].update_sensory(agent, world.entities)
            world.prune_events()
            al.inbox.drain()

            sensory = al.sensory

            # ═══ observing 闭环检测 ═══
            if agent.expects_reply:
                result = check_observing(agent, sensory)
                if result:
                    continue

            # ═══ Layered KL ═══
            drives = al.drives
            coins = round(float(agent.get("interaction").private_attrs.get("coins", 0)))
            kl_text = total_kl(agent, sensory, drives, coins)

            if not kl_text:
                await asyncio.sleep(0.3)
                continue

            # ═══ INTENT check ═══
            latest_mem = al.memory.latest()
            if latest_mem and latest_mem.get("text", "").startswith("INTENT:"):
                mem_age = time.time() - latest_mem["ts"]
                if mem_age < 30:
                    intent_action = latest_mem["text"][len("INTENT:"):].strip()
                    intent_target = systems["interaction"].find_entity_at(
                        agent.zone, agent.pos, intent_action, world.entities, exclude_id=agent.id)
                    if intent_target and systems["interaction"].can_interact(agent, intent_target):
                        action_name = systems["interaction"].fuzzy_match_action(intent_target, intent_action)
                        if action_name:
                            result = await systems["interaction"].interact(
                                agent, intent_target, action_name, {}, world)
                            agent.last_action_time = world.clock.now()
                            latest_mem["text"] += " ✓"
                            trace = {"agent": name, "ts": time.time()-test_start,
                                     "wall": datetime.now().isoformat(), "zone": agent.zone, "pos": list(agent.pos),
                                     "target": intent_target.name, "target_id": intent_target.id,
                                     "action_text": intent_action, "action_count": actions+1,
                                     "note": "from_intent", "result_narrative": result.narrative if result else ""}
                            agent_traces[name].append(trace)
                            log("action", agent=name, action=intent_action, target=intent_target.name, ts=trace["ts"])
                            actions += 1
                            snapshot_p(agent, sensory, drives, coins)
                            await asyncio.sleep(0.3)
                            continue
                    latest_mem["text"] = f"STALE: {intent_action}"

            # ═══ Decide ═══
            visible_text = ""
            if sensory.get_visible_only():
                visible_text = "\n".join(f"id={r.entity_id}|{r.name}|dist={r.distance}" for r in sensory.get_visible_only())

            ctx = {
                "round": actions+1, "name": agent.name, "personality": al.personality,
                "drives_table": al.drives.to_prompt_table(),
                "zone_name": world.zones.get(agent.zone,{}).get("name",""),
                "zone_width": world.zones.get(agent.zone,{}).get("width",10),
                "zone_height": world.zones.get(agent.zone,{}).get("height",10),
                "pos_x": agent.pos[0], "pos_y": agent.pos[1],
                "interactable_text": sensory.to_prompt_vision(),
                "visible_text": visible_text,
                "memory_text": al.memory.to_prompt_text(5),
                "messages_text": "", "hearing_text": sensory.to_prompt_hearing(),
                "kl_text": kl_text,
            }

            prompt1 = assembler.assemble("agent_decision", ctx)
            t1 = time.time()
            decision = await brain.decide(ctx)
            dt1 = time.time()-t1

            move_to = decision.get("move_to")
            action_text = decision.get("action")

            trace = {
                "agent": name, "ts": time.time()-test_start,
                "wall": datetime.now().isoformat(), "zone": agent.zone, "pos": list(agent.pos),
                "drives": {k:round(v,1) for k,v in drives.attrs.items() if k in ("thirst","hunger","social","energy","fun","mood")},
                "coins": coins, "kl_text": kl_text, "llm1_prompt": prompt1,
                "llm1_time": round(dt1,1), "llm1_output": decision,
            }

            if move_to and isinstance(move_to, list) and len(move_to)==2:
                agent.move_to(move_to); agent.last_action_time=world.clock.now()
                systems["sensory"].update(agent, world.entities, world)
                systems["interaction"].update_sensory(agent, world.entities)
                trace["moved_to"] = move_to

            if action_text:
                target = systems["interaction"].find_entity_at(agent.zone, agent.pos, action_text, world.entities, exclude_id=agent.id)
                if target and systems["interaction"].can_interact(agent, target):
                    action_name = systems["interaction"].fuzzy_match_action(target, action_text)
                    if action_name:
                        result = await systems["interaction"].interact(
                            agent, target, action_name, decision, world)
                        agent.last_action_time = world.clock.now(); actions += 1
                        trace.update({
                            "target": target.name, "target_id": target.id,
                            "action_text": action_text, "action_name": action_name,
                            "action_count": actions,
                        })
                        if result:
                            trace["result_narrative"] = result.narrative
                            trace["result_caller_deltas"] = result.caller_deltas
                            trace["result_target_deltas"] = result.target_deltas
                        agent_traces[name].append(trace)
                        log("action", agent=name, action=action_text, target=target.name, ts=trace["ts"])

                        # Enter observing if expects_reply
                        if decision.get("expects_reply") and target.has("agent"):
                            agent.expects_reply = True
                            agent.observing_target = target.id
                            agent.observing_since = time.time()
                            agent.observing_timeout = decision.get("patience", 5)
                    else:
                        trace["note"] = f"no matching action on {target.name}"
                        agent_traces[name].append(trace)
                elif target and not systems["interaction"].can_interact(agent, target):
                    agent.move_to(list(target.pos))
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world)
                    systems["interaction"].update_sensory(agent, world.entities)
                    trace["moved_to"] = list(target.pos)
                    trace["note"] = f"moving to {target.name}"
                    agent_traces[name].append(trace)
                    al.memory.record(f"INTENT: {action_text}", ts=time.time())
                else:
                    if not target:
                        trace["note"] = f"no target at pos ({agent.pos})"
                        agent_traces[name].append(trace)
            else:
                if not move_to:
                    trace["note"] = "rest"
                agent_traces[name].append(trace)

            snapshot_p(agent, sensory, drives, coins)
            await asyncio.sleep(0)

        except Exception as e:
            import traceback; traceback.print_exc()
            log("error", agent=name, error=str(e))
            await asyncio.sleep(3)


# ═══════════ Validation ═══════════
def validate_traces(traces: list) -> dict:
    issues = []
    npc_names = {'杰洛特','兰伯特','凯拉','卓尔坦','叶奈法','特莉丝','维瑟米尔','丹德里恩'}
    acted = [t for t in traces if t.get('action_text')]
    for t in acted:
        for dkey in ['result_caller_deltas', 'result_target_deltas']:
            deltas = t.get(dkey, {})
            for attr, val in deltas.items():
                if isinstance(val, (int, float)) and attr != 'coins' and abs(val) > 30:
                    issues.append(f"[{t['ts']:.0f}s] {t['agent']}→{t.get('target','')} {attr}={val} (large)")
    for t in traces:
        drives = t.get('drives', {})
        for attr, val in drives.items():
            if isinstance(val, (int, float)) and val < 0:
                issues.append(f"[{t['ts']:.0f}s] {t['agent']} {attr}={val} (negative!)")
    npc_acts = [t for t in acted if t.get('target') in npc_names and t['agent'] in npc_names and t['agent']!=t['target']]
    return {"issues": issues, "total_actions": len(acted), "npc_actions": len(npc_acts)}


async def main():
    with open(os.path.join(BASE,"config/world.yaml")) as f: wc=yaml.safe_load(f)
    with open(os.path.join(BASE,"config/llm.yaml")) as f: lc=yaml.safe_load(f)
    loader=PromptLoader(os.path.join(BASE,"config/prompts.yaml")); assembler=PromptAssembler(loader)
    llm=LLMClient(lc); brain=Brain(llm,assembler)
    systems={"sensory":SensorySystem(),"interaction":InteractionSystem(llm, assembler),"decay":DecaySystem()}
    world=World(wc,systems)

    for npc in EXTRA_NPCS:
        world.register_external_agent(npc["id"],npc["name"],npc["zone"],npc["pos"],personality=npc["personality"])
        e=world.entities[npc["id"]]
        e.get("interaction").private_attrs.update({k:v for k,v in npc.items() if k in ("coins","hunger","thirst","social","energy","fun","mood")})
        e.get("agent").drives=DriveSystem(attrs=e.get("interaction").private_attrs,
                                           decay_rates={"thirst":0.022,"hunger":0.018,"social":0.015,"energy":-0.01,"fun":0.015})

    agent_ids=["geralt","yennefer","dandelion","vesemir","triss","zoltan","keira","lambert"]
    agents=[world.entities[a] for a in agent_ids]
    log("test_start", agents=agent_ids, n_entities=len(world.entities))
    print("="*70, flush=True)
    print(f"  E2E — observing + layered KL | {len(agents)} agents | 60s", flush=True)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print("="*70, flush=True)

    runtime = 60
    tasks = [run_agent(a, world, brain, assembler, systems, runtime) for a in agents]
    await asyncio.gather(*tasks)

    elapsed = time.time()-test_start
    merged = [t for traces in agent_traces.values() for t in traces]
    merged.sort(key=lambda t: t["ts"])
    with open(OUT,"w") as f: json.dump(merged, f, ensure_ascii=False, indent=2)

    agents_seen = set(agent_traces.keys())
    actions = [t for traces in agent_traces.values() for t in traces if t.get("action_text")]
    results = [t for traces in agent_traces.values() for t in traces if t.get("result_narrative")]

    print(f"\n{'='*70}", flush=True)
    print(f"  Complete: {sum(len(v) for v in agent_traces.values())} traces, {len(actions)} actions, {len(results)} results, {elapsed:.0f}s", flush=True)
    for name in sorted(agents_seen):
        agent_acts = [t for t in actions if t["agent"]==name]
        agent_res = [t for t in results if t["agent"]==name]
        print(f"  {name:6s}: {len(agent_acts)} acts, {len(agent_res)} results", flush=True)
    print(f"  Data: {OUT}", flush=True)

    report = validate_traces(merged)
    if report["issues"]:
        print(f"\n  ⚠️  {len(report['issues'])} issues:", flush=True)
        for iss in report["issues"][:10]:
            print(f"    - {iss}", flush=True)
    else:
        print(f"  ✅ All checks passed.", flush=True)
    print(f"  Total actions: {report['total_actions']} | NPC→NPC: {report['npc_actions']}", flush=True)


if __name__=="__main__":
    asyncio.run(main())
