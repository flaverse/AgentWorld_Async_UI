#!/usr/bin/env python3
"""Quick full test — 8 agents, 60s each, generate comprehensive report."""
import sys,os,yaml,asyncio,uuid,json,time
from datetime import datetime
from collections import defaultdict, Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World; from agent.brain import Brain
from agent.drives import DriveSystem; from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler; from llm.client import LLMClient
from systems.sensory import SensorySystem; from systems.interaction import InteractionSystem
from systems.decay import DecaySystem; from interaction.resolver import InteractionResolver
from layers.interaction import ActionDef, TargetType, ResolveType

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "test_full_log.jsonl")
REPORT = os.path.join(BASE, "test_full_report.json")
log_entries = []

def log(etype, **kw):
    e = {"ts": time.time() - t0, "wall": datetime.now().isoformat(), "event": etype, **kw}
    log_entries.append(e)
    with open(LOG, "a") as f: f.write(json.dumps(e, ensure_ascii=False) + "\n")

t0 = time.time()

EXTRA = [
    {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[20,8],"personality":"老猎魔人","coins":200,"thirst":50,"hunger":40,"social":30,"mood":55},
    {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],"personality":"女术士","coins":300,"thirst":35,"hunger":45,"social":25,"mood":50},
    {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[15,10],"personality":"矮人商人","coins":500,"thirst":65,"hunger":50,"social":60,"mood":70},
    {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],"personality":"年轻女术士","coins":150,"thirst":30,"hunger":55,"social":15,"mood":60},
    {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],"personality":"猎魔人","coins":100,"thirst":70,"hunger":60,"social":15,"mood":40},
]

async def main():
    with open(os.path.join(BASE,"config/world.yaml")) as f: wc = yaml.safe_load(f)
    with open(os.path.join(BASE,"config/llm.yaml")) as f: lc = yaml.safe_load(f)
    loader = PromptLoader(os.path.join(BASE,"config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(lc); brain = Brain(llm, assembler); resolver = InteractionResolver(llm, assembler)
    systems = {"sensory": SensorySystem(), "interaction": InteractionSystem(resolver), "decay": DecaySystem()}
    world = World(wc, systems)

    for npc in EXTRA:
        world.register_external_agent(npc["id"], npc["name"], npc["zone"], npc["pos"], personality=npc["personality"])
        e = world.entities[npc["id"]]
        e.get("interaction").private_attrs.update({k: v for k, v in npc.items() if k in ("coins", "hunger", "thirst", "social", "energy", "fun", "mood")})
        e.get("agent").drives = DriveSystem(attrs=e.get("interaction").private_attrs, decay_rates={"thirst": 0.022, "hunger": 0.018, "social": 0.015, "energy": -0.01, "fun": 0.015})

    agent_ids = ["geralt", "yennefer", "dandelion", "vesemir", "triss", "zoltan", "keira", "lambert"]
    agents = [world.entities[a] for a in agent_ids]
    log("test_start", agents=agent_ids, n_entities=len(world.entities))

    print("=" * 60, flush=True)
    print(f"  Full Log Test — 8 agents × 60s each", flush=True)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)

    all_stats = {}; act_types = Counter()
    per_agent = 60

    for i, agent in enumerate(agents):
        name = agent.name; al = agent.get("agent"); acts = 0; zc = 0; errs = 0
        end = time.time() + per_agent
        log("agent_begin", agent=name, zone=agent.zone, pos=list(agent.pos))

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
                    log("result", agent=name, narrative=r.narrative[:150], deltas=r.caller_deltas, zone_change=bool(r.move_to_zone))

                al.inbox.drain()

                if agent.status == "idle":
                    sensory = al.sensory
                    ctx = {
                        "round": acts + 1, "name": agent.name, "personality": al.personality,
                        "drives_table": al.drives.to_prompt_table(),
                        "zone_name": world.zones.get(agent.zone, {}).get("name", ""),
                        "zone_width": 40, "zone_height": 30,
                        "pos_x": agent.pos[0], "pos_y": agent.pos[1],
                        "interactable_text": sensory.to_prompt_vision(),
                        "visible_text": "", "memory_text": al.memory.to_prompt_text(3),
                        "messages_text": "", "hearing_text": al.sensory.to_prompt_hearing(),
                    }
                    d = await brain.decide(ctx)
                    mv = d.get("move_to")
                    if mv and isinstance(mv, list) and len(mv) == 2:
                        agent.move_to(mv); agent.last_action_time = world.clock.now()
                        systems["sensory"].update(agent, world.entities, world)
                        systems["interaction"].update_sensory(agent, world.entities)
                    tid = d.get("target_entity"); an = d.get("action")
                    if tid and an and tid in world.entities:
                        tgt = world.entities[tid]; il = tgt.get("interaction")
                        if il and il.get_action(an) if il else False:
                            ad = il.get_action(an)
                            if ad.target_type.value == "passive":
                                if systems["interaction"].can_interact(agent, tgt):
                                    systems["interaction"].submit(uuid.uuid4().hex[:8], agent, tgt, an, world)
                                    agent.last_action_time = world.clock.now(); acts += 1
                                    act_types[an] += 1
                                    log("action", agent=name, zone=agent.zone, action=an, target=tgt.name, resolve=ad.resolve.value)
                            elif ad.target_type.value == "agent":
                                world.send_message(agent.id, tid, an, f"{agent.name}想和你{an}")
                                acts += 1; act_types[an] += 1
                                log("action", agent=name, action=an, target=tgt.name, type="agent")
                        elif il:
                            # Free-text action — auto accepted
                            if systems["interaction"].can_interact(agent, tgt):
                                systems["interaction"].submit(uuid.uuid4().hex[:8], agent, tgt, an, world)
                                agent.last_action_time = world.clock.now(); acts += 1
                                act_types[an] += 1
                                log("action", agent=name, action=an, target=tgt.name, type="free_text")

                await asyncio.sleep(2 if agent.status == "busy" else 1.5)
            except Exception as e:
                errs += 1; log("error", agent=name, error=str(e)); await asyncio.sleep(3)

        # Drain final
        for _ in range(30):
            if agent.busy_result is not None:
                r = agent.busy_result; agent.busy_result = None
                systems["interaction"].apply_result(r, agent, world)
                if r.move_to_zone: zc += 1
                break
            await asyncio.sleep(1)

        pa = agent.get("interaction").private_attrs
        stats = {"name": name, "actions": acts, "zone_changes": zc, "errors": errs,
                 "zone": agent.zone, "thirst": round(pa.get("thirst", 0), 1),
                 "coins": round(pa.get("coins", 0), 1), "mood": round(pa.get("mood", 0), 1),
                 "memories": [e.get("narrative", "")[:80] for e in al.memory.entries[-3:]]}
        all_stats[name] = stats
        log("agent_end", **stats)
        pct = (i + 1) / len(agents) * 100
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {name}: {acts} act, zc={zc}, err={errs} | {pct:.0f}%", flush=True)

        # Check attributes
        ok = 0; fail = 0
        for attr in ["thirst", "hunger", "social", "energy", "fun", "mood"]:
            v = pa.get(attr, 0)
            if 0 <= v <= 100: ok += 1
            else: fail += 1; print(f"    ❌ {attr}={v}", flush=True)
        if pa.get("coins", 0) >= 0: ok += 1
        else: fail += 1; print(f"    ❌ coins={pa['coins']}", flush=True)
        print(f"    attrs: {ok}/{ok+fail}", flush=True)

    # Generate report
    report = {
        "test": "Full Log — 8 agents × 60s",
        "generated": datetime.now().isoformat(),
        "elapsed_s": time.time() - t0,
        "agents": [all_stats[a] for a in agent_ids if a in all_stats],
        "action_types": dict(act_types.most_common()),
        "total_actions": sum(s["actions"] for s in all_stats.values()),
        "total_zone_changes": sum(s["zone_changes"] for s in all_stats.values()),
        "total_errors": sum(s["errors"] for s in all_stats.values()),
        "log_entries": len(log_entries),
        "result_samples": [e for e in log_entries if e["event"] == "result"][:10],
        "action_samples": [e for e in log_entries if e["event"] == "action"][:20],
    }

    with open(REPORT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}", flush=True)
    print(f"  Report: {REPORT}  |  Log: {LOG}", flush=True)
    print(f"  Actions: {report['total_actions']}  |  Zone: {report['total_zone_changes']}  |  Errors: {report['total_errors']}", flush=True)
    print(f"  Types: {dict(act_types.most_common(8))}", flush=True)
    print(f"  Log entries: {len(log_entries)}", flush=True)

    log("test_end", total_actions=report["total_actions"], total_zone_changes=report["total_zone_changes"], total_errors=report["total_errors"])

if __name__ == "__main__":
    asyncio.run(main())
