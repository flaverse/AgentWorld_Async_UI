#!/usr/bin/env python3
"""1-Hour Endurance: 8 agents sequentially, ~7.5 min each. Simple loop."""
import sys,os,yaml,asyncio,uuid,json,time
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World
from agent.brain import Brain
from agent.drives import DriveSystem
from layers.interaction import ActionDef, TargetType, ResolveType
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from interaction.resolver import InteractionResolver

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE, "test_1hour_log.jsonl")
REPORT_PATH = os.path.join(BASE, "test_1hour_report.json")

EXTRA_NPCS = [
    {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[20,8],
     "personality":"狼学派最年长的猎魔人，杰洛特的导师。沉稳老练，偶尔来酒馆小酌。",
     "coins":200,"thirst":50,"hunger":40,"social":30,"energy":60,"fun":35,"mood":55},
    {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],
     "personality":"诺维格瑞的女术士，寻找盟友对抗神殿审判。",
     "coins":300,"thirst":35,"hunger":45,"social":25,"energy":75,"fun":30,"mood":50},
    {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[15,10],
     "personality":"矮人商人，嗓门大爱喝酒。杰洛特的老朋友。",
     "coins":500,"thirst":65,"hunger":50,"social":60,"energy":55,"fun":70,"mood":70},
    {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],
     "personality":"年轻女术士，对炼金术和古籍充满热情。",
     "coins":150,"thirst":30,"hunger":55,"social":15,"energy":80,"fun":45,"mood":60},
    {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],
     "personality":"狼学派猎魔人，年轻气盛，说话刻薄但内心善良。",
     "coins":100,"thirst":70,"hunger":60,"social":15,"energy":70,"fun":20,"mood":40},
]

test_start = time.time()
log_entries = []

def log(etype, **kw):
    entry = {"ts":time.time()-test_start, "wall":datetime.now().isoformat(), "event":etype, **kw}
    log_entries.append(entry)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False)+"\n")

async def run_one(agent, world, brain, systems, name, seconds):
    """Run one agent for `seconds` seconds."""
    al = agent.get("agent")
    end = time.time() + seconds
    actions = 0
    zc = 0
    errs = 0
    log("agent_begin", agent=name)

    while time.time() < end:
        try:
            elapsed = max(world.clock.now() - agent.last_action_time, 0)
            systems["decay"].tick(agent, elapsed)
            systems["sensory"].update(agent, world.entities, world)
            systems["interaction"].update_sensory(agent, world.entities)
            world.prune_events()

            if agent.busy_result is not None:
                r = agent.busy_result; agent.busy_result = None
                systems["interaction"].apply_result(r, agent, world)
                if r.move_to_zone: zc += 1
                log("result", agent=name, narrative=r.narrative[:120],
                    deltas=r.caller_deltas, zone_change=bool(r.move_to_zone))

            if agent.status == "idle":
                sensory = al.sensory
                ctx = {
                    "round": actions+1, "name": agent.name,
                    "personality": al.personality,
                    "drives_table": al.drives.to_prompt_table(),
                    "zone_name": world.zones.get(agent.zone,{}).get("name",""),
                    "zone_width": world.zones.get(agent.zone,{}).get("width",10),
                    "zone_height": world.zones.get(agent.zone,{}).get("height",10),
                    "pos_x": agent.pos[0], "pos_y": agent.pos[1],
                    "interactable_text": sensory.to_prompt_vision(),
                    "visible_text": "", "memory_text": al.memory.to_prompt_text(3),
                    "messages_text": "", "hearing_text": sensory.to_prompt_hearing(),
                }
                d = await brain.decide(ctx)

                mv = d.get("move_to")
                if mv and isinstance(mv,list) and len(mv)==2:
                    agent.move_to(mv)
                    agent.last_action_time = world.clock.now()
                    systems["sensory"].update(agent, world.entities, world)
                    systems["interaction"].update_sensory(agent, world.entities)

                tid = d.get("target_entity")
                an = d.get("action")
                if tid and an and tid in world.entities:
                    tgt = world.entities[tid]
                    il = tgt.get("interaction")
                    if il and il.get_action(an):
                        ad = il.get_action(an)
                        if ad.target_type.value == "passive":
                            if systems["interaction"].can_interact(agent, tgt):
                                systems["interaction"].submit(uuid.uuid4().hex[:8], agent, tgt, an, world)
                                agent.last_action_time = world.clock.now()
                                actions += 1
                                log("action", agent=name, action=an, target=tgt.name, resolve=ad.resolve.value)
                        elif ad.target_type.value == "agent":
                            world.send_message(agent.id, tid, an, f"{agent.name}想和你{an}")
                            actions += 1
                            log("action", agent=name, action=an, target=tgt.name, type="agent")

            await asyncio.sleep(2.0 if agent.status=="busy" else 1.5)

        except Exception as e:
            errs += 1
            log("error", agent=name, error=str(e))
            await asyncio.sleep(3)

    # Drain final
    for _ in range(30):
        if agent.busy_result is not None:
            r = agent.busy_result; agent.busy_result = None
            systems["interaction"].apply_result(r, agent, world)
            if r.move_to_zone: zc += 1
            break
        await asyncio.sleep(1)

    elapsed = time.time() - (end - seconds)
    log("agent_end", agent=name, actions=actions, zone_changes=zc, errors=errs, elapsed_s=elapsed)
    pa = agent.get("interaction").private_attrs
    return {"name":name, "actions":actions, "zone_changes":zc, "errors":errs,
            "elapsed_s":elapsed, "zone":agent.zone, "pos":list(agent.pos),
            "thirst":pa.get("thirst",0), "coins":pa.get("coins",0),
            "mood":pa.get("mood",0), "social":pa.get("social",0)}


async def main():
    global test_start; test_start = time.time()
    with open(LOG_PATH, "w") as f: f.write("")

    with open(os.path.join(BASE,"config","world.yaml")) as f: wc = yaml.safe_load(f)
    with open(os.path.join(BASE,"config","llm.yaml")) as f: lc = yaml.safe_load(f)
    loader = PromptLoader(os.path.join(BASE,"config","prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(lc)
    brain = Brain(llm, assembler)
    resolver = InteractionResolver(llm, assembler)
    systems = {"sensory":SensorySystem(), "interaction":InteractionSystem(resolver), "decay":DecaySystem()}
    world = World(wc, systems)

    for npc in EXTRA_NPCS:
        world.register_external_agent(npc["id"], npc["name"], npc["zone"], npc["pos"], personality=npc["personality"])
        e = world.entities[npc["id"]]
        e.get("interaction").private_attrs.update({k:v for k,v in npc.items() if k in ("coins","hunger","thirst","social","energy","fun","mood")})
        e.get("agent").drives = DriveSystem(attrs=e.get("interaction").private_attrs, decay_rates={"thirst":0.022,"hunger":0.018,"social":0.015,"energy":-0.01,"fun":0.015})

    agent_ids = ["geralt","yennefer","dandelion","vesemir","triss","zoltan","keira","lambert"]
    agents = [world.entities[a] for a in agent_ids]

    log("test_start", n_entities=len(world.entities), n_zones=len(world.zones), agents=agent_ids)

    print("=" * 60, flush=True)
    print(f"  1-Hour Endurance — {len(agents)} agents × {len(world.zones)} zones", flush=True)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)
    for a in agents:
        pa = a.get("interaction").private_attrs
        print(f"  {a.name:6s} {a.zone:10s} thirst={pa['thirst']:.0f} coins={pa['coins']}", flush=True)
    print(flush=True)

    per_agent = 420  # 7 min per agent → 56 min total + overhead ≈ 1 hour
    results = []

    for i, agent in enumerate(agents):
        name = agent.name
        r = await run_one(agent, world, brain, systems, name, per_agent)
        results.append(r)

        elapsed = time.time() - test_start
        pct = (i+1)/len(agents)*100
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {name}: {r['actions']} actions, "
              f"{r['zone_changes']} zc, {r['errors']} err | "
              f"thirst={r['thirst']:.0f} coins={r['coins']:.0f} mood={r['mood']:.0f} | {pct:.0f}%", flush=True)

    total_elapsed = time.time() - test_start
    total_actions = sum(r["actions"] for r in results)
    total_zc = sum(r["zone_changes"] for r in results)
    total_err = sum(r["errors"] for r in results)

    # Attribute checks
    ok, fail = 0, 0
    for r in results:
        for attr in ["thirst","mood","social"]:
            v = r.get(attr, 0)
            if 0 <= v <= 100: ok += 1
            else: fail += 1
        if r["coins"] >= 0: ok += 1
        else: fail += 1

    print("\n" + "=" * 60, flush=True)
    print(f"  Done. Elapsed: {total_elapsed/60:.1f} min", flush=True)
    print(f"  Actions: {total_actions} | Zone changes: {total_zc} | Errors: {total_err}", flush=True)
    print(f"  Attributes: {ok}/{ok+fail}", flush=True)
    print(f"  {'✅ PASSED' if fail==0 else '❌ FAILED'}", flush=True)

    report = {
        "test": "1-Hour Endurance — 8 NPCs × 3 Zones",
        "generated": datetime.now().isoformat(),
        "elapsed_s": total_elapsed,
        "total_actions": total_actions,
        "total_zone_changes": total_zc,
        "total_errors": total_err,
        "attr_checks": {"passed": ok, "failed": fail},
        "agents": results,
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log("test_end", **{k:report[k] for k in ["total_actions","total_zone_changes","total_errors","elapsed_s"]})
    print(f"  Report: {REPORT_PATH}", flush=True)
    print(f"  Log: {LOG_PATH}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
