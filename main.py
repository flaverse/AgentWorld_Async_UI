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


# ═══════════════════════════════════════════════════
#  Config loading
# ═══════════════════════════════════════════════════

def load_config():
    """Load world, prompt, and LLM configs. Returns structured dict."""
    with open(os.path.join(base_dir, "config/world.yaml")) as f:
        wc = yaml.safe_load(f)
    with open(os.path.join(base_dir, "config/llm.yaml")) as f:
        lc = yaml.safe_load(f)
    loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    labels = loader.data.get("text_labels", {})
    return {"world": wc, "llm": lc, "assembler": assembler, "labels": labels}


# ═══════════════════════════════════════════════════
#  World setup
# ═══════════════════════════════════════════════════

def make_world(world_cfg: dict, llm_cfg: dict, assembler):
    """Create World + systems + brain from configs. Returns (world, brain, systems)."""
    llm = LLMClient(llm_cfg)
    brain = Brain(llm, assembler)
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(llm, assembler),
        "decay": DecaySystem(),
    }
    return World(world_cfg, systems), brain, systems


def get_agents(world: World) -> list:
    """Return all autonomous agents from the world."""
    return [e for e in world.entities.values()
            if e.get("agent") and e.get("agent").autonomous]


def setup_agent_drives(agents: list, sim: dict, currency: str) -> None:
    """Ensure every agent has a DriveSystem with the configured decay rates and thresholds."""
    decay_rates = sim.get("decay_rates", {})
    drive = sim.get("drive", {})
    for e in agents:
        if not e.get("agent").drives and e.has("interaction"):
            e.get("agent").drives = DriveSystem(
                attrs=e.get("interaction").private_attrs,
                decay_rates=decay_rates,
                currency_key=currency,
                drive_min=drive.get("min", 0),
                drive_max=drive.get("max", 100),
                urgent_threshold=drive.get("urgent_threshold", 80),
                needed_threshold=drive.get("needed_threshold", 60))
        inter = e.get("interaction")
        if inter:
            inter.currency_key = currency
            inter.drive_min = drive.get("min", 0)
            inter.drive_max = drive.get("max", 100)


# ═══════════════════════════════════════════════════
#  Runner
# ═══════════════════════════════════════════════════

async def run_concurrent(agents, world, brain, assembler, systems,
                         runtime: float, cfg: dict,
                         *, trace_fn=None):
    """Run all agents concurrently."""
    tasks = [run_agent(a, world, brain, assembler, systems,
                       runtime, trace_fn=trace_fn, cfg=cfg)
             for a in agents]
    await asyncio.gather(*tasks)


# ═══════════════════════════════════════════════════
#  Tracing
# ═══════════════════════════════════════════════════

class TraceCollector:
    """Collect and merge traces from concurrent agent runs."""

    def __init__(self):
        self.start_time = time.time()
        self._traces: dict[str, list] = defaultdict(list)

    def callback(self):
        """Return a trace_fn suitable for run_agent()."""
        collector = self
        def fn(trace):
            trace["ts"] = time.time() - collector.start_time
            trace["wall"] = datetime.now().isoformat()
            collector._traces[trace["agent"]].append(trace)
        return fn

    def merged(self) -> list[dict]:
        traces = [t for per_agent in self._traces.values() for t in per_agent]
        traces.sort(key=lambda t: t.get("ts", 0))
        return traces

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.merged(), f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════
#  Reporting
# ═══════════════════════════════════════════════════

def report(collector: TraceCollector, agents: list, sim: dict,
           elapsed: float, validate: bool, output_path: str):
    """Print summary and optional validation report."""
    merged = collector.merged()
    if output_path:
        collector.save(output_path)

    actions = [t for t in merged if t.get("action_text")]
    results = [t for t in merged if t.get("result_narrative")]

    print(f"  Complete: {len(merged)} traces, {len(actions)} actions, "
          f"{len(results)} results, {elapsed:.0f}s")
    for name in sorted(set(t.get("agent","") for t in merged)):
        agent_acts = [t for t in actions if t["agent"] == name]
        print(f"    {name:6s}: {len(agent_acts)} acts")
    if output_path:
        print(f"  Data: {output_path}")

    if not validate:
        return

    npc_names = {a.name for a in agents}
    npc_acts = sum(1 for t in actions
                   if t.get("target") in npc_names
                   and t.get("agent","") in npc_names
                   and t["agent"] != t["target"])

    v = sim.get("validation", {})
    delta_max = v.get("delta_max", 30)
    drive_min = v.get("drive_min", 0)
    drive_max = v.get("drive_max", 100)
    currency = sim.get("currency", "coins")
    issues = []
    for t in actions:
        for dkey in ['result_caller_deltas', 'result_target_deltas']:
            for attr, val in t.get(dkey, {}).items():
                if isinstance(val, (int, float)) and attr != currency and abs(val) > delta_max:
                    issues.append(f"large delta: {t['agent']} {attr}={val}")
    for t in merged:
        drives = t.get('drives', {})
        for attr, val in drives.items():
            if attr == currency:
                continue  # currency has no min/max
            if isinstance(val, (int, float)) and (val < drive_min or val > drive_max):
                issues.append(f"drive out of range: {t['agent']} {attr}={val}")
    if issues:
        print(f"\n  ⚠️  {len(issues)} issues:")
        for i in issues[:10]:
            print(f"    - {i}")
    else:
        print(f"  ✅ All validation checks passed.")
    print(f"  total_actions={len(actions)} npc_npc={npc_acts}")


# ═══════════════════════════════════════════════════
#  Entry points
# ═══════════════════════════════════════════════════

async def cmd_test(args):
    """Run concurrent test: all agents from config."""
    cfg = load_config()
    sim = cfg["world"]["world"].get("simulation", {})
    currency = sim.get("currency", "coins")
    world, brain, systems = make_world(cfg["world"], cfg["llm"], cfg["assembler"])
    agents = get_agents(world)
    if not agents:
        print("No autonomous agents found in world.yaml.")
        return
    setup_agent_drives(agents, sim, currency)

    kl = sim.get("kl", {})
    loop_cfg = {
        "poll_interval": sim.get("poll_interval", 0.3),
        "thresholds": kl.get("state_thresholds", [30, 60, 80]),
        "coin_epsilon": kl.get("coin_epsilon", 5),
        "stale_timeout": sim.get("stale_timeout", 30),
        "currency": currency,
        "text": sim.get("text", {}),
        "labels": cfg["labels"],
        "intent_ttl": sim.get("intent_ttl", 30),
        "default_patience": sim.get("default_patience", 5),
        "speech_window": sim.get("speech_window", 30),
        "memory_prompt_count": sim.get("memory_prompt_count", 5),
    }

    print(f"\n{'='*60}")
    print(f"  AgentWorld Async — {cfg['world']['world']['name']}")
    print(f"  {len(agents)} agents | {args.runtime}s | Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    tracer = TraceCollector()
    t_start = time.time()
    await run_concurrent(agents, world, brain, cfg["assembler"],
                         systems, args.runtime, loop_cfg,
                         trace_fn=tracer.callback())
    elapsed = time.time() - t_start
    report(tracer, agents, sim, elapsed, args.validate, args.output)


async def cmd_demo(args):
    """Run single-agent demo."""
    cfg = load_config()
    world, brain, systems = make_world(cfg["world"], cfg["llm"], cfg["assembler"])
    agents = get_agents(world)
    if not agents:
        print("No autonomous agents found.")
        return
    agent = agents[0]
    sim = cfg["world"]["world"].get("simulation", {})

    print(f"Agent: {agent.name} | personality: {agent.get('agent').personality}")
    print(f"{'='*50}")

    await run_agent(agent, world, brain, cfg["assembler"],
                    systems,
                    runtime=30, cfg={"labels": cfg["labels"]},
                    trace_fn=lambda t: print(
                        f"  [{agent.name}] → {t.get('target','?')} | "
                         f"{t.get('action_text','?')[:80]}"))


# ═══════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(description="AgentWorld Async")
    parser.add_argument("--demo", action="store_true",
                        help="Run single-agent demo")
    parser.add_argument("--runtime", type=int, default=60,
                        help="Test runtime in seconds (default: 60)")
    parser.add_argument("--validate", action="store_true",
                        help="Run validation checks after test")
    parser.add_argument("--output", type=str, default="",
                        help="Save trace JSON to file")
    return parser.parse_args()


async def main():
    args = parse_args()
    if args.demo:
        await cmd_demo(args)
    else:
        await cmd_test(args)


if __name__ == "__main__":
    asyncio.run(main())
