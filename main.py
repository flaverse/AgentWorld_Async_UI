#!/usr/bin/env python3
"""AgentWorld Async — single entry point. World-agnostic.

  python main.py                         # 8-agent concurrent test (60s)
  python main.py --runtime 180 --validate  # 3min + validation
  python main.py --demo                  # single-agent demo
  python main.py --output trace.json     # save trace data
"""
import sys, os, yaml, asyncio, json, time, argparse
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
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from loop import run_agent


async def test_mode(args):
    """Run concurrent test. All agents auto-detected from world.yaml."""
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

    # ── Auto-detect all autonomous agents from world.yaml ──
    agents = [e for e in world.entities.values()
              if e.get("agent") and e.get("agent").autonomous]
    if not agents:
        print("No autonomous agents found in world.yaml.")
        return

    # ── Read simulation config ──
    sim = wc.get("world", {}).get("simulation", {})
    decay_rates = sim.get("decay_rates", {})
    kl_config = {
        "thresholds": sim.get("kl", {}).get("state_thresholds", [30, 60, 80]),
        "coin_epsilon": sim.get("kl", {}).get("coin_epsilon", 5),
        "stale_timeout": sim.get("stale_timeout", 30),
    }
    val_config = sim.get("validation", {})
    delta_max = val_config.get("delta_max", 30)
    drive_min = val_config.get("drive_min", 0)
    drive_max = val_config.get("drive_max", 100)
    currency = sim.get("currency", "coins")

    # ── Ensure all agents have DriveSystem ──
    for e in agents:
        if not e.get("agent").drives and e.has("interaction"):
            e.get("agent").drives = DriveSystem(
                attrs=e.get("interaction").private_attrs,
                decay_rates=decay_rates)

    t_start = time.time()
    all_traces: dict[str, list] = defaultdict(list)

    def make_tracer():
        def fn(trace):
            trace["ts"] = time.time() - t_start
            trace["wall"] = datetime.now().isoformat()
            all_traces[trace["agent"]].append(trace)
        return fn

    runtime = args.runtime
    print(f"\n{'='*60}")
    print(f"  AgentWorld Async — {wc['world']['name']}")
    print(f"  {len(agents)} agents | {runtime}s | Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    tasks = [run_agent(a, world, brain, assembler, systems, runtime,
                       trace_fn=make_tracer(), kl_config=kl_config)
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
        npc_names = {a.name for a in agents}
        npc_acts = sum(1 for t in actions
                       if t.get("target") in npc_names
                       and t.get("agent","") in npc_names
                       and t["agent"] != t["target"])
        issues = []
        for t in actions:
            for dkey in ['result_caller_deltas', 'result_target_deltas']:
                deltas = t.get(dkey, {})
                for attr, val in deltas.items():
                    if isinstance(val, (int, float)) and attr != currency and abs(val) > delta_max:
                        issues.append(f"large delta: {t['agent']} {attr}={val}")
        for t in merged:
            drives = t.get('drives', {})
            for attr, val in drives.items():
                if isinstance(val, (int, float)) and (val < drive_min or val > drive_max):
                    issues.append(f"drive out of range: {t['agent']} {attr}={val}")
        if issues:
            print(f"\n  ⚠️  {len(issues)} issues:")
            for i in issues[:10]:
                print(f"    - {i}")
        else:
            print(f"  ✅ All validation checks passed.")
        print(f"  total_actions={len(actions)} npc_npc={npc_acts}")


async def demo_mode():
    """Single-agent demo."""
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
    sim = wc.get("world", {}).get("simulation", {})
    kl_config = {
        "thresholds": sim.get("kl", {}).get("state_thresholds", [30, 60, 80]),
        "coin_epsilon": sim.get("kl", {}).get("coin_epsilon", 5),
        "stale_timeout": sim.get("stale_timeout", 30),
    }

    print(f"Agent: {agent.name} | personality: {agent.get('agent').personality}")
    print(f"{'='*50}")

    await run_agent(agent, world, brain, assembler, systems, runtime=30,
                    trace_fn=lambda t: print(
                        f"  [{agent.name}] → {t.get('target','?')} | "
                        f"{t.get('action_text','?')[:80]}"),
                    kl_config=kl_config)


async def main():
    parser = argparse.ArgumentParser(description="AgentWorld Async")
    parser.add_argument("--demo", action="store_true",
                        help="Run single-agent demo")
    parser.add_argument("--runtime", type=int, default=60,
                        help="Test runtime in seconds (default: 60)")
    parser.add_argument("--validate", action="store_true",
                        help="Run validation checks after test")
    parser.add_argument("--output", type=str, default="",
                        help="Save trace JSON to file")
    args = parser.parse_args()

    if args.demo:
        await demo_mode()
    else:
        await test_mode(args)


if __name__ == "__main__":
    asyncio.run(main())
