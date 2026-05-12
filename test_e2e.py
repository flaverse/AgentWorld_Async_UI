#!/usr/bin/env python3
"""E2E integration test — 3 min, all 8 agents, full pipeline trace with timestamps."""
import sys,os,yaml,asyncio,uuid,json,time
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World; from agent.brain import Brain; from agent.drives import DriveSystem
from prompt.loader import PromptLoader; from prompt.assembler import PromptAssembler
from llm.client import LLMClient; from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem; from systems.decay import DecaySystem
from interaction.resolver import InteractionResolver
from core.verification import Verifier, build_feedback
from layers.interaction import ActionDef, TargetType, ResolveType

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(BASE, "e2e_trace.json")
LOG_FILE = os.path.join(BASE, "e2e_log.jsonl")

EXTRA_NPCS = [
    {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[20,8],"personality":"老猎魔人","coins":200,"thirst":50,"social":30,"mood":55},
    {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],"personality":"女术士","coins":300,"thirst":35,"social":25,"mood":50},
    {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[15,10],"personality":"矮人商人","coins":500,"thirst":65,"social":60,"mood":70},
    {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],"personality":"年轻女术士","coins":150,"thirst":30,"social":15,"mood":60},
    {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],"personality":"猎魔人","coins":100,"thirst":70,"social":15,"mood":40},
]

test_start = time.time()

def log(etype, **kw):
    e = {"ts": time.time()-test_start, "wall": datetime.now().isoformat(), "event": etype, **kw}
    with open(LOG_FILE, "a") as f: f.write(json.dumps(e, ensure_ascii=False)+"\n")

all_traces = []

async def run_one(agent, world, brain, assembler, systems, resolver, name, seconds):
    al = agent.get("agent")
    end = time.time() + seconds
    actions = 0

    while time.time() < end:
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
            pa = agent.get("interaction").private_attrs
            print(f"   result: {r.narrative[:50]}... | thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0):.0f}", flush=True)

        al.inbox.drain()

        if agent.status == "idle":
            sensory = al.sensory
            # Build context
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

            # LLM #1
            prompt1 = assembler.assemble("agent_decision", ctx)
            t1 = time.time(); decision = await brain.decide(ctx); dt1 = time.time()-t1

            move_to = decision.get("move_to")
            action = decision.get("action")

            # Trace entry
            trace = {
                "agent": name, "ts": time.time()-test_start,
                "wall": datetime.now().isoformat(),
                "zone": agent.zone, "pos": list(agent.pos),
                "drives": {k:round(v,1) for k,v in al.drives.attrs.items() if k in ("thirst","hunger","social","energy","fun","mood")},
                "coins": round(agent.get("interaction").private_attrs.get("coins",0)),
                "llm1_prompt": prompt1, "llm1_time": round(dt1,1),
                "llm1_output": decision,
            }

            # Move
            if move_to and isinstance(move_to, list) and len(move_to)==2:
                agent.move_to(move_to); agent.last_action_time=world.clock.now()
                systems["sensory"].update(agent, world.entities, world)
                systems["interaction"].update_sensory(agent, world.entities)
                trace["moved_to"] = move_to

            # Action
            if action:
                target = systems["interaction"].find_entity_at(agent.zone, agent.pos, action, world.entities)
                if target and systems["interaction"].can_interact(agent, target):
                    # Build LLM #2 context
                    il = target.get("interaction")
                    ambient = world.get_ambient_entities(target, radius=2, exclude={agent.id})
                    label_table = resolver._build_label_mapping(world.entities)
                    caller_memory = al.memory.to_prompt_text(3)

                    rctx = {
                        "caller_name": agent.name,
                        "caller_recent_memory": caller_memory or "无",
                        "caller_public": json.dumps(il.public_attrs if il else {}, ensure_ascii=False),
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
                        "action_text": action,
                        "action_count": actions,
                    })
                    all_traces.append(trace)
                    log("action", agent=name, action=action, target=target.name, ts=trace["ts"])
                    print(f"  [{name}] {action[:40]}... → {target.name} (LLM1={dt1:.1f}s)", flush=True)
                else:
                    if not move_to and not action:
                        pass  # rest
                    elif not target:
                        trace["note"] = "no target found at pos"
                        all_traces.append(trace)
            else:
                if not move_to:
                    trace["note"] = "rest"
                all_traces.append(trace)

            await asyncio.sleep(2 if agent.status=="busy" else 1.2)
        else:
            await asyncio.sleep(1.2)

    # Drain final
    for _ in range(20):
        if agent.busy_result is not None:
            r=agent.busy_result; agent.busy_result=None
            systems["interaction"].apply_result(r, agent, world)
            break
        await asyncio.sleep(0.5)

    log("agent_end", agent=name, actions=actions)


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
    print("="*60, flush=True)
    print(f"  E2E Integration Test — {len(agents)} agents × ~22s each", flush=True)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print("="*60, flush=True)

    per_agent = 21  # ~21s each → ~2.8 min total
    for i, agent in enumerate(agents):
        name=agent.name
        print(f"\n[{i+1}/8] {name} ({world.zones[agent.zone]['name']}) {agent.pos[0]},{agent.pos[1]}", flush=True)
        await run_one(agent, world, brain, assembler, systems, resolver, name, per_agent)
        pa=agent.get("interaction").private_attrs
        print(f"  done: thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0):.0f} mood={pa.get('mood',0):.0f}", flush=True)

    elapsed = time.time()-test_start
    with open(OUT_FILE,"w") as f: json.dump(all_traces, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}", flush=True)
    print(f"  Complete: {len(all_traces)} traces, {elapsed:.0f}s", flush=True)
    print(f"  Data: {OUT_FILE}", flush=True)

if __name__=="__main__":
    asyncio.run(main())
