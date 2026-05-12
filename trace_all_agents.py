#!/usr/bin/env python3
"""Trace full pipeline for all 8 agents. One interaction each."""
import sys,os,yaml,asyncio,uuid,json,time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World; from agent.brain import Brain
from agent.drives import DriveSystem
from prompt.loader import PromptLoader; from prompt.assembler import PromptAssembler
from llm.client import LLMClient; from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem; from systems.decay import DecaySystem
from interaction.resolver import InteractionResolver
from core.verification import Verifier, build_feedback

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(BASE, "pipeline_trace_all.json")

EXTRA_NPCS = [
    {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[20,8],"personality":"老猎魔人","coins":200,"thirst":50,"social":30,"mood":55},
    {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],"personality":"女术士","coins":300,"thirst":35,"social":25,"mood":50},
    {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[15,10],"personality":"矮人商人","coins":500,"thirst":65,"social":60,"mood":70},
    {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],"personality":"年轻女术士","coins":150,"thirst":30,"social":15,"mood":60},
    {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],"personality":"猎魔人","coins":100,"thirst":70,"social":15,"mood":40},
]

trace_data = []

async def trace_one(agent, world, brain, assembler, systems, resolver):
    name = agent.name; al = agent.get("agent")
    systems["sensory"].update(agent, world.entities, world)
    systems["interaction"].update_sensory(agent, world.entities)

    # Build LLM #1 context
    sensory = al.sensory
    pa = agent.get("interaction").private_attrs
    zone_data = world.get_zone_data(agent.zone)

    ctx = {
        "round": 1, "name": agent.name, "personality": al.personality,
        "drives_table": al.drives.to_prompt_table(),
        "zone_name": zone_data.get("name", ""),
        "zone_width": zone_data.get("width", 10), "zone_height": zone_data.get("height", 10),
        "pos_x": agent.pos[0], "pos_y": agent.pos[1],
        "interactable_text": sensory.to_prompt_vision(),
        "visible_text": "", "memory_text": "无", "messages_text": "",
        "hearing_text": sensory.to_prompt_hearing(),
    }

    prompt1 = assembler.assemble("agent_decision", ctx)
    t1 = time.time(); decision = await brain.decide(ctx); dt1 = time.time() - t1
    if not isinstance(decision, dict):
        return {"agent": name, "error": f"LLM returned {type(decision).__name__}", "llm1_prompt": prompt1,
                "llm1_output": str(decision)[:300], "llm1_time": dt1}

    tid = decision.get("target_entity"); an = decision.get("action")
    if not tid or not an or tid not in world.entities:
        return {"agent": name, "error": "no valid target", "llm1_prompt": prompt1,
                "llm1_output": decision, "llm1_time": dt1}

    target = world.entities[tid]; il = target.get("interaction")
    ambient = world.get_ambient_entities(target, radius=2, exclude={agent.id})
    comp = systems["interaction"].build_component(target, world.entities, radius=3)

    # LLM #2
    rctx = {
        "caller_name": agent.name,
        "caller_public": json.dumps(il.public_attrs, ensure_ascii=False) if il else "{}",
        "caller_private": json.dumps(agent.get("interaction").private_attrs, ensure_ascii=False) if agent.has("interaction") else "{}",
        "target_name": target.name,
        "target_public": json.dumps(il.public_attrs, ensure_ascii=False) if il else "{}",
        "target_private": json.dumps(il.private_attrs, ensure_ascii=False) if il else "{}",
        "action": an, "ambient_text": resolver._format_ambient(ambient),
    }
    prompt2 = assembler.assemble("interaction_resolve", rctx)
    t2 = time.time()
    result = await resolver.resolve(caller=agent, target=target, action=an,
                                     ambient_entities=ambient, world=world)
    dt2 = time.time() - t2

    # Verify deltas
    with open(os.path.join(BASE,"config/prompts.yaml")) as f:
        pc = yaml.safe_load(f)
    v = Verifier(mask=pc["verification"]["projection_mask"])
    effects = [{"entity_id": agent.id, "deltas": result.caller_deltas},
               {"entity_id": tid, "deltas": result.target_deltas}] + result.ambient_effects
    failures = v.verify(effects, world.entities)
    fb = build_feedback(failures) if failures else ""

    trace = {
        "agent": name, "zone": agent.zone, "pos": list(agent.pos),
        "target": target.name, "target_id": tid,
        "action": an,
        "free_text": bool(not (il and il.get_action(an))),
        "component": [c["name"] for c in comp],
        "llm1_prompt": prompt1, "llm1_output": decision, "llm1_time": round(dt1, 1),
        "llm2_prompt": prompt2, "llm2_narrative": result.narrative,
        "llm2_caller_deltas": result.caller_deltas,
        "llm2_target_deltas": result.target_deltas,
        "llm2_ambient_effects": result.ambient_effects,
        "llm2_public_observation": result.public_observation,
        "llm2_time": round(dt2, 1),
        "verify_failures": len(failures), "verify_feedback": fb[:200] if fb else "pass",
    }
    return trace


async def main():
    with open(os.path.join(BASE,"config/world.yaml")) as f: wc=yaml.safe_load(f)
    with open(os.path.join(BASE,"config/llm.yaml")) as f: lc=yaml.safe_load(f)
    loader = PromptLoader(os.path.join(BASE,"config/prompts.yaml"))
    assembler = PromptAssembler(loader); llm = LLMClient(lc)
    brain = Brain(llm, assembler); resolver = InteractionResolver(llm, assembler)
    systems = {"sensory": SensorySystem(), "interaction": InteractionSystem(resolver), "decay": DecaySystem()}
    world = World(wc, systems)

    for npc in EXTRA_NPCS:
        world.register_external_agent(npc["id"], npc["name"], npc["zone"], npc["pos"], personality=npc["personality"])
        e = world.entities[npc["id"]]
        e.get("interaction").private_attrs.update({k: v for k, v in npc.items() if k in ("coins", "hunger", "thirst", "social", "energy", "fun", "mood")})
        e.get("agent").drives = DriveSystem(attrs=e.get("interaction").private_attrs,
                                             decay_rates={"thirst": 0.022, "hunger": 0.018, "social": 0.015, "energy": -0.01, "fun": 0.015})

    agents = [world.entities[a] for a in ["geralt", "yennefer", "dandelion", "vesemir", "triss", "zoltan", "keira", "lambert"]]
    print("=" * 60, flush=True)
    print("  Full Pipeline Trace — All 8 Agents", flush=True)
    print("=" * 60, flush=True)

    for i, agent in enumerate(agents):
        print(f"[{i+1}/8] {agent.name}...", flush=True)
        trace = await trace_one(agent, world, brain, assembler, systems, resolver)
        trace_data.append(trace)
        pa = agent.get("interaction").private_attrs
        print(f"  -> {trace['action'][:60]}... | free={trace['free_text']} | "
              f"LLM#1={trace['llm1_time']}s LLM#2={trace['llm2_time']}s "
              f"verify={trace['verify_failures']} fail", flush=True)

    with open(OUT_FILE, "w") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {OUT_FILE}", flush=True)
    print(f"Total time: {sum(t['llm1_time']+t['llm2_time'] for t in trace_data):.0f}s", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
