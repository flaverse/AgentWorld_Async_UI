#!/usr/bin/env python3
"""E2E CONCURRENT test — all 8 agents run simultaneously for 180s."""
import sys,os,yaml,asyncio,uuid,json,time
from datetime import datetime
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World; from agent.brain import Brain; from agent.drives import DriveSystem
from prompt.loader import PromptLoader; from prompt.assembler import PromptAssembler
from llm.client import LLMClient; from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem; from systems.decay import DecaySystem
from interaction.resolver import InteractionResolver
from layers.interaction import ActionDef, TargetType, ResolveType

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "e2e_concurrent_trace.json")
LOG = os.path.join(BASE, "e2e_concurrent_log.jsonl")

EXTRA_NPCS = [
    {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[20,8],"personality":"老猎魔人","coins":200,"thirst":50,"social":30,"mood":55},
    {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],"personality":"女术士","coins":300,"thirst":35,"social":25,"mood":50},
    {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[15,10],"personality":"矮人商人","coins":500,"thirst":65,"social":60,"mood":70},
    {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],"personality":"年轻女术士","coins":150,"thirst":30,"social":15,"mood":60},
    {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],"personality":"猎魔人","coins":100,"thirst":70,"social":15,"mood":40},
]

test_start = time.time()
agent_traces: dict[str, list] = defaultdict(list)

def log(etype, **kw):
    e = {"ts": time.time()-test_start, "wall": datetime.now().isoformat(), "event": etype, **kw}
    with open(LOG, "a") as f: f.write(json.dumps(e, ensure_ascii=False)+"\n")


async def run_agent(agent, world, brain, assembler, systems, resolver, runtime):
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

            # Busy result
            if agent.busy_result is not None:
                r = agent.busy_result; agent.busy_result = None
                systems["interaction"].apply_result(r, agent, world)
                log("result", agent=name, narrative=r.narrative[:150], deltas=r.caller_deltas)

            al.inbox.drain()

            if agent.status == "idle":
                sensory = al.sensory
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
                    "memory_text": al.memory.to_prompt_text(3),
                    "messages_text": "", "hearing_text": sensory.to_prompt_hearing(),
                }

                prompt1 = assembler.assemble("agent_decision", ctx)
                t1 = time.time(); decision = await brain.decide(ctx); dt1 = time.time()-t1

                move_to = decision.get("move_to")
                action = decision.get("action")

                trace = {
                    "agent": name, "ts": time.time()-test_start,
                    "wall": datetime.now().isoformat(),
                    "zone": agent.zone, "pos": list(agent.pos),
                    "drives": {k:round(v,1) for k,v in al.drives.attrs.items() if k in ("thirst","hunger","social","energy","fun","mood")},
                    "coins": round(agent.get("interaction").private_attrs.get("coins",0)),
                    "llm1_prompt": prompt1, "llm1_time": round(dt1,1),
                    "llm1_output": decision,
                }

                if move_to and isinstance(move_to, list) and len(move_to)==2:
                    agent.move_to(move_to); agent.last_action_time=world.clock.now()
                    systems["sensory"].update(agent, world.entities, world)
                    systems["interaction"].update_sensory(agent, world.entities)
                    trace["moved_to"] = move_to

                if action:
                    target = systems["interaction"].find_entity_at(agent.zone, agent.pos, action, world.entities, exclude_id=agent.id)
                    if target and systems["interaction"].can_interact(agent, target):
                        il = target.get("interaction")
                        ambient = world.get_ambient_entities(target, radius=2, exclude={agent.id})
                        label_table = resolver._build_label_mapping(world.entities)
                        caller_memory = al.memory.to_prompt_text(3)

                        rctx = {
                            "caller_name": agent.name,
                            "caller_recent_memory": caller_memory or "无",
                            "caller_public": json.dumps(il.public_attrs, ensure_ascii=False) if il else "{}",
                            "caller_private": json.dumps(agent.get("interaction").private_attrs, ensure_ascii=False) if agent.has("interaction") else "{}",
                            "target_name": target.name,
                            "target_public": json.dumps(il.public_attrs, ensure_ascii=False) if il else "{}",
                            "target_private": json.dumps(il.private_attrs, ensure_ascii=False) if il else "{}",
                            "action": action,
                            "ambient_text": resolver._format_ambient(ambient),
                            "label_table": label_table,
                        }
                        prompt2 = assembler.assemble("interaction_resolve", rctx)

                        t2 = time.time()
                        systems["interaction"].submit(uuid.uuid4().hex[:8], agent, target, action, world)
                        agent.last_action_time = world.clock.now(); actions += 1
                        dt2 = time.time()-t2

                        trace.update({
                            "llm2_prompt": prompt2, "llm2_time": round(dt2,1),
                            "target": target.name, "target_id": target.id,
                            "action_text": action, "action_count": actions,
                        })
                        agent_traces[name].append(trace)
                        log("action", agent=name, action=action, target=target.name, ts=trace["ts"])
                    else:
                        if not move_to and not action: pass
                        elif not target:
                            trace["note"] = f"no target at pos ({agent.pos})"
                            agent_traces[name].append(trace)
                else:
                    if not move_to:
                        trace["note"] = "rest"
                    agent_traces[name].append(trace)

            # Attach result to latest trace when it arrives
            if agent_traces[name] and agent_traces[name][-1].get("agent") == name and agent.busy_result is not None:
                r = agent.busy_result; agent.busy_result = None
                systems["interaction"].apply_result(r, agent, world)
                agent_traces[name][-1]["result_narrative"] = r.narrative
                agent_traces[name][-1]["result_caller_deltas"] = r.caller_deltas
                agent_traces[name][-1]["result_target_deltas"] = r.target_deltas

            await asyncio.sleep(2 if agent.status=="busy" else 1.0)

        except Exception as e:
            import traceback; traceback.print_exc()
            log("error", agent=name, error=str(e))
            await asyncio.sleep(3)


async def main():
    with open(os.path.join(BASE,"config/world.yaml")) as f: wc=yaml.safe_load(f)
    with open(os.path.join(BASE,"config/llm.yaml")) as f: lc=yaml.safe_load(f)
    loader=PromptLoader(os.path.join(BASE,"config/prompts.yaml")); assembler=PromptAssembler(loader)
    llm=LLMClient(lc); brain=Brain(llm,assembler); resolver=InteractionResolver(llm,assembler)
    systems={"sensory":SensorySystem(),"interaction":InteractionSystem(resolver),"decay":DecaySystem()}
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
    print(f"  E2E CONCURRENT — {len(agents)} agents running simultaneously for 180s", flush=True)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print("="*70, flush=True)

    runtime = 180  # 3 min concurrent
    tasks = [run_agent(a, world, brain, assembler, systems, resolver, runtime) for a in agents]
    await asyncio.gather(*tasks)

    # Wait for pending resolver results
    print("\n  Waiting for pending resolvers...", flush=True)
    pending = {}
    for a in agents:
        if a.busy_result is not None:
            pending[a.name] = a
    for _ in range(30):
        if not pending: break
        for name, a in list(pending.items()):
            if a.busy_result is not None:
                r = a.busy_result; a.busy_result = None
                systems["interaction"].apply_result(r, a, world)
                log("result", agent=name, narrative=r.narrative[:150], deltas=r.caller_deltas)
                # Attach to last trace for this agent
                for t in reversed(agent_traces.get(name, [])):
                    if t.get("agent") == name and not t.get("result_narrative"):
                        t["result_narrative"] = r.narrative
                        t["result_caller_deltas"] = r.caller_deltas
                        t["result_target_deltas"] = r.target_deltas
                        break
                del pending[name]
            elif a.status == "idle":
                del pending[name]
        await asyncio.sleep(1)
    if pending:
        print(f"  ⚠️ {len(pending)} agents still pending: {list(pending.keys())}", flush=True)

    elapsed = time.time()-test_start
    merged = [t for traces in agent_traces.values() for t in traces]
    merged.sort(key=lambda t: t["ts"])
    with open(OUT,"w") as f: json.dump(merged, f, ensure_ascii=False, indent=2)

    # Stats
    agents_seen = set(agent_traces.keys())
    actions = [t for traces in agent_traces.values() for t in traces if t.get("action_text")]
    results = [t for traces in agent_traces.values() for t in traces if t.get("result_narrative")]

    print(f"\n{'='*70}", flush=True)
    print(f"  Complete: {sum(len(v) for v in agent_traces.values())} traces, {len(actions)} actions, {len(results)} results, {elapsed:.0f}s", flush=True)
    for name in sorted(agents_seen):
        agent_acts = [t for t in actions if t["agent"]==name]
        agent_res = [t for t in results if t["agent"]==name]
        agent_social = [t for traces in agent_traces.values() for t in traces if t["agent"]==name and t.get("target") and t["agent"]!=t["target"]]
        print(f"  {name:6s}: {len(agent_acts)} acts, {len(agent_res)} results, {len(agent_social)} social", flush=True)
    print(f"  Data: {OUT}", flush=True)

if __name__=="__main__":
    asyncio.run(main())
