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
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from loop import run_agent, LoopConfig
from core.director import Director
from gateway import WorldGateway


# ═══════════════════════════════════════════════════
#  Config loading
# ═══════════════════════════════════════════════════

def load_config(world_path: str | None = None):
    """Load world, prompt, and LLM configs. Returns structured dict."""
    w_path = world_path or os.path.join(base_dir, "config/world.yaml")
    with open(w_path) as f:
        wc = yaml.safe_load(f)
    with open(os.path.join(base_dir, "config/llm.yaml")) as f:
        lc = yaml.safe_load(f)
    loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    labels = loader.data.get("text_labels", {})
    labels["sensory_prompts"] = loader.data.get("sensory_prompts", {})
    return {"world": wc, "llm": lc, "assembler": assembler, "labels": labels}


# ═══════════════════════════════════════════════════
#  World setup
# ═══════════════════════════════════════════════════

def spawn_world(cfg: dict):
    """Create World, Brain, and Systems from loaded config.
    Returns (world, brain, systems_dict).
    """
    llm = LLMClient(cfg["llm"])
    brain = Brain(llm, cfg["assembler"])
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(llm, cfg["assembler"]),
        "decay": DecaySystem(),
    }
    return World(cfg["world"], systems), brain, systems


def get_autonomous_agents(world: World) -> list:
    """Return entities that have AgentLayer and are autonomous."""
    return [e for e in world.entities.values()
            if e.has("agent") and e.get("agent").autonomous]


def build_loop_config(sim: dict, labels: dict) -> LoopConfig:
    """Construct LoopConfig from YAML simulation block.
    All params sourced from sim dict with safe defaults.
    """
    kl = sim.get("kl", {})
    return LoopConfig(
        poll_interval=sim.get("poll_interval", 0.3),
        thresholds=kl.get("state_thresholds", [30, 60, 80]),
        coin_epsilon=kl.get("coin_epsilon", 5),
        stale_timeout=sim.get("stale_timeout", 30),
        currency=sim.get("currency", "coins"),
        text=sim.get("text", {}),
        labels=labels,
        default_patience=sim.get("default_patience", 5),
        memory_prompt_count=sim.get("memory_prompt_count", 5),
    )


def setup_agent_drives(agents: list, sim: dict, currency: str) -> None:
    """Inject per-attribute drive config into existing DriveSystem + InteractionLayer."""
    drive_cfg = sim.get("drive", {})
    attr_cfg = drive_cfg.get("attributes", {})
    for e in agents:
        al = e.get("agent")
        inter = e.get("interaction")
        if al and al.drives:
            al.drives.attr_cfg = attr_cfg
        if inter:
            inter.attr_bounds = {k: {"min": v.get("min", 0), "max": v.get("max", 100)}
                                 for k, v in attr_cfg.items()}
            inter.currency_key = currency


# ═══════════════════════════════════════════════════
#  Runner
# ═══════════════════════════════════════════════════

async def run_concurrent(agents, world, brain, assembler, systems,
                         runtime: float, cfg: LoopConfig,
                         *, trace_fn=None, director=None):
    """Run all agents concurrently."""
    tasks = [run_agent(a, world, brain, assembler, systems,
                       runtime, trace_fn=trace_fn, cfg=cfg,
                       director=director)
             for a in agents]
    await asyncio.gather(*tasks, return_exceptions=True)


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
        deltas = t.get('result_caller_deltas')
        if not isinstance(deltas, dict): continue
        for attr, val in deltas.items():
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
    cfg = load_config(args.world or None)
    sim = cfg["world"]["world"].get("simulation", {})
    world, brain, systems = spawn_world(cfg)
    agents = get_autonomous_agents(world)
    if not agents:
        print("No autonomous agents found in world.yaml.")
        return
    setup_agent_drives(agents, sim, sim.get("currency", "coins"))
    loop_cfg = build_loop_config(sim, cfg["labels"])

    # ── Director + Gateway (external agent access) ──
    director = Director(world)
    gateway = WorldGateway(world, director)
    api_task = None
    if args.api_port:
        from gateway.api import create_app
        app = create_app(gateway, poll_interval=sim.get("poll_interval", 0.3))
        import uvicorn
        api_config = uvicorn.Config(app, host="0.0.0.0", port=args.api_port, log_level="warning")
        api_server = uvicorn.Server(api_config)
        api_task = asyncio.create_task(api_server.serve())
        print(f"  Gateway API: http://0.0.0.0:{args.api_port}")

    print(f"\n{'='*60}")
    print(f"  AgentWorld Async — {cfg['world']['world']['name']}")
    print(f"  {len(agents)} agents | {args.runtime}s | Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    tracer = TraceCollector()
    t_start = time.time()

    if args.persist:
        from core.persistence import WorldDB
        db = WorldDB(args.persist)
        run_id = db.start_run(cfg['world']['world']['name'])
    else:
        db = None
        run_id = ""

    await run_concurrent(agents, world, brain, cfg["assembler"],
                         systems, args.runtime, loop_cfg,
                         trace_fn=tracer.callback(), director=director)

    # Stop API
    if api_task:
        api_server.should_exit = True
        api_task.cancel()
        try:
            await api_task
        except (asyncio.CancelledError, Exception):
            pass

    elapsed = time.time() - t_start
    report(tracer, agents, sim, elapsed, args.validate, args.output)
    if db:
        db.end_run(run_id)
        db.close()
        print(f"  Persisted to: {args.persist}")


async def cmd_demo(args):
    """Run single-agent demo."""
    cfg = load_config(args.world or None)
    sim = cfg["world"]["world"].get("simulation", {})
    world, brain, systems = spawn_world(cfg)
    agents = get_autonomous_agents(world)
    if not agents:
        print("No autonomous agents found.")
        return
    agent = agents[0]
    setup_agent_drives(agents, sim, sim.get("currency", "coins"))
    loop_cfg = build_loop_config(sim, cfg["labels"])

    print(f"Agent: {agent.name} | personality: {agent.get('agent').personality}")
    print(f"{'='*50}")

    await run_agent(agent, world, brain, cfg["assembler"],
                    systems,
                    runtime=30, cfg=loop_cfg,
                    trace_fn=lambda t: print(
                        f"  [{agent.name}] → {t.get('target','?')} | "
                         f"{t.get('action_text','?')[:80]}"))


# ═══════════════════════════════════════════════════
#  Config validation
# ═══════════════════════════════════════════════════

def cmd_validate_config(args):
    """Validate world.yaml + prompts.yaml schema without running agents."""
    errors = []
    cfg = load_config(args.world or None)

    # 1. Check world has required top-level keys
    world = cfg["world"]
    for key in ["world", "zones", "entities"]:
        if key not in world:
            errors.append(f"world.yaml missing key: {key}")

    # 2. Check every entity has required keys
    for e in world.get("entities", []):
        if "id" not in e: errors.append(f"Entity missing id")
        if "zone" not in e: errors.append(f"Entity '{e.get('name',e.get('id','?'))}' missing zone")

    # 3. Check prompts.yaml: every template's slot exists in the slots registry
    loader = cfg["assembler"].loader
    all_slots = loader.data.get("slots", {})
    for tpl_name, tpl in loader.data.get("templates", {}).items():
        for slot_name in tpl.get("slots", []):
            if slot_name not in all_slots:
                errors.append(f"Template '{tpl_name}' references undefined slot '{slot_name}'")

    # 4. Check every slot's condition is a known ctx key or empty
    known_ctx = {"main_thread", "name", "personality", "drives_table", "kl_text",
                 "zone_name", "sensory_text", "memory_text", "messages_text",
                 "interactable_text", "visible_text", "hearing_text", "round",
                 "caller_name", "caller_id", "target_name", "target_id"}
    for slot_name, slot in all_slots.items():
        cond = slot.get("condition", "")
        if cond and cond not in known_ctx:
            errors.append(f"Slot '{slot_name}' has unknown condition '{cond}' (not in known ctx keys)")

    # 5. Check sensory_prompts channels
    sp = loader.data.get("sensory_prompts", {})
    for ch_name in sp:
        if "header" not in sp[ch_name]:
            errors.append(f"sensory_prompts.{ch_name} missing 'header'")

    if errors:
        print(f"❌ Config validation FAILED ({len(errors)} issues):")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"✅ Config validation PASSED")
        zones = len(world.get("zones", []))
        entities = len(world.get("entities", []))
        agents = sum(1 for e in world.get("entities", []) if "agent" in e)
        print(f"   {zones} zones, {entities} entities, {agents} agents")
        print(f"   {len(all_slots)} slots defined, {len(loader.data.get('templates', {}))} templates")


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
    parser.add_argument("--persist", type=str, default="",
                        help="SQLite database path for persistence")
    parser.add_argument("--validate-config", action="store_true",
                        help="Validate world.yaml + prompts.yaml without running")
    parser.add_argument("--world", type=str, default="",
                        help="Path to world YAML (default: config/world.yaml)")
    parser.add_argument("--eval-report", type=str, default="",
                        help="Run evaluation report from existing trace JSON")
    parser.add_argument("--api-port", type=int, default=0,
                        help="Start Gateway API on given port (0=disabled)")
    return parser.parse_args()


async def main():
    args = parse_args()
    if args.eval_report:
        from eval import run_eval
        report = run_eval(args.eval_report)
        print(report.to_table())
        if args.output:
            report.save(args.output)
            print(f"\n  Saved: {args.output}")
        return
    if args.validate_config:
        cmd_validate_config(args)
        return
    if args.demo:
        await cmd_demo(args)
    else:
        await cmd_test(args)


if __name__ == "__main__":
    asyncio.run(main())
