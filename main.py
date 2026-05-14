#!/usr/bin/env python3
"""AgentWorld Async — single entry point.

  python main.py                    # API server + demo loop
  python main.py --test             # 8-agent concurrent test (60s)
  python main.py --test --runtime 180 --validate  # 3min + validation
"""
import sys, os, yaml, asyncio, json, time, logging, argparse
from datetime import datetime
from collections import defaultdict

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "src"))

from core.world import World
from agent.brain import Brain
from agent.drives import DriveSystem
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem, check_observing
from systems.decay import DecaySystem
from loop import run_agent


EXTRA_NPCS = [
    {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[7,2],"personality":"老猎魔人","coins":200,"thirst":50,"social":30,"mood":55},
    {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],"personality":"女术士","coins":300,"thirst":35,"social":25,"mood":50},
    {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[7,2],"personality":"矮人商人","coins":500,"thirst":65,"social":60,"mood":70},
    {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],"personality":"年轻女术士","coins":150,"thirst":30,"social":15,"mood":60},
    {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],"personality":"猎魔人","coins":100,"thirst":70,"social":15,"mood":40},
]


def validate_traces(traces: list) -> list[str]:
    """Post-run consistency checks."""
    issues = []
    npc_names = {'杰洛特','兰伯特','凯拉','卓尔坦','叶奈法','特莉丝','维瑟米尔','丹德里恩'}
    acted = [t for t in traces if t.get('action_text')]
    for t in acted:
        for dkey in ['result_caller_deltas', 'result_target_deltas']:
            deltas = t.get(dkey, {})
            for attr, val in deltas.items():
                if isinstance(val, (int, float)) and attr != 'coins' and abs(val) > 30:
                    issues.append(f"large delta: {t['agent']} {attr}={val}")
    for t in traces:
        drives = t.get('drives', {})
        for attr, val in drives.items():
            if isinstance(val, (int, float)) and val < 0:
                issues.append(f"negative drive: {t['agent']} {attr}={val}")
    npc_acts = [t for t in acted if t.get('target') in npc_names and t['agent'] in npc_names and t['agent']!=t['target']]
    issues.append(f"total_actions={len(acted)} npc_npc={len(npc_acts)}")
    return issues


async def test_mode(args):
    """Run 8-agent concurrent test with optional trace."""
    with open(os.path.join(base_dir, "config/world.yaml")) as f:
        wc = yaml.safe_load(f)
    with open(os.path.join(base_dir, "config/llm.yaml")) as f:
        lc = yaml.safe_load(f)

    loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(lc)
    brain = Brain(llm, assembler)

    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(llm, assembler),
        "decay": DecaySystem(),
    }
    world = World(wc, systems)

    for npc in EXTRA_NPCS:
        world.register_external_agent(npc["id"], npc["name"], npc["zone"],
                                       npc["pos"], personality=npc["personality"])
        e = world.entities[npc["id"]]
        e.get("interaction").private_attrs.update(
            {k: v for k, v in npc.items()
             if k in ("coins","hunger","thirst","social","energy","fun","mood")})
        e.get("agent").drives = DriveSystem(
            attrs=e.get("interaction").private_attrs,
            decay_rates={"thirst":0.022,"hunger":0.018,"social":0.015,"energy":-0.01,"fun":0.015})

    agent_ids = ["geralt","yennefer","dandelion","vesemir","triss","zoltan","keira","lambert"]
    agents = [world.entities[a] for a in agent_ids]

    t_start = time.time()
    all_traces: dict[str, list] = defaultdict(list)

    def make_tracer():
        def fn(trace):
            trace["ts"] = time.time() - t_start
            trace["wall"] = datetime.now().isoformat()
            trace["zone"] = agents[0].zone  # placeholder, traced agent will overwrite
            all_traces[trace["agent"]].append(trace)
        return fn

    runtime = args.runtime
    print(f"\n{'='*60}")
    print(f"  AgentWorld Async — Test Mode")
    print(f"  {len(agents)} agents | {runtime}s | Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    tasks = [run_agent(a, world, brain, assembler, systems, runtime,
                       trace_fn=make_tracer())
             for a in agents]
    await asyncio.gather(*tasks)

    elapsed = time.time() - t_start
    merged = [t for traces in all_traces.values() for t in traces]
    merged.sort(key=lambda t: t.get("ts", 0))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

    actions = [t for t in merged if t.get("action_text")]
    results = [t for t in merged if t.get("result_narrative")]
    print(f"  Complete: {len(merged)} traces, {len(actions)} actions, "
          f"{len(results)} results, {elapsed:.0f}s")
    for name in sorted(set(t.get("agent","") for t in merged)):
        agent_acts = [t for t in actions if t["agent"] == name]
        print(f"    {name:6s}: {len(agent_acts)} acts")
    if args.output:
        print(f"  Data: {args.output}")

    if args.validate:
        issues = validate_traces(merged)
        real_issues = [i for i in issues if not i.startswith("total_actions")]
        if real_issues:
            print(f"\n  ⚠️  {len(real_issues)} issues:")
            for i in real_issues:
                print(f"    - {i}")
        else:
            print(f"  ✅ All validation checks passed.")
        print(f"  {[i for i in issues if i.startswith('total_actions')][0]}")


async def demo_mode():
    """Single-agent demo loop (original main.py behavior)."""
    with open(os.path.join(base_dir, "config/world.yaml")) as f:
        wc = yaml.safe_load(f)
    with open(os.path.join(base_dir, "config/llm.yaml")) as f:
        lc = yaml.safe_load(f)

    loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(lc)
    brain = Brain(llm, assembler)

    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(llm, assembler),
        "decay": DecaySystem(),
    }
    world = World(wc, systems)

    agents = [e for e in world.entities.values()
              if e.get("agent") and e.get("agent").autonomous]
    if not agents:
        print("No autonomous agents found.")
        return

    agent = agents[0]
    print(f"Agent: {agent.name} | personality: {agent.get('agent').personality}")
    print(f"{'='*50}")

    await run_agent(agent, world, brain, assembler, systems, runtime=30,
                    trace_fn=lambda t: print(
                        f"  [{agent.name}] → {t.get('target','?')} | "
                        f"{t.get('action_text','?')[:80]}"))


async def main():
    parser = argparse.ArgumentParser(description="AgentWorld Async")
    parser.add_argument("--test", action="store_true",
                        help="Run 8-agent concurrent test")
    parser.add_argument("--runtime", type=int, default=60,
                        help="Test runtime in seconds (default: 60)")
    parser.add_argument("--validate", action="store_true",
                        help="Run validation checks after test")
    parser.add_argument("--output", type=str, default="",
                        help="Save trace JSON to file")
    parser.add_argument("--debug", action="store_true",
                        help="Show stderr (LLM parse errors etc)")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.WARNING)

    if args.test:
        await test_mode(args)
    else:
        await demo_mode()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
