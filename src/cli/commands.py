"""CLI command implementations: test, demo, validate-config."""
import time
import asyncio
from datetime import datetime

from .config import load_config
from .world_setup import spawn_world, get_autonomous_agents
from .loop_factory import build_loop_config, setup_agent_drives
from .runner import run_concurrent, TraceCollector
from .report import report


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

    from core.clock import DecisionClock
    telemetry = cfg["telemetry"]
    max_cc = max((g.limit for g in cfg["concurrency_gates"].values()), default=1)
    if telemetry.warmed_up:
        measured_tick = telemetry.median_latency * len(agents) / max(max_cc, 1)
        decision_tick = max(2.0, measured_tick)
    else:
        decision_tick = max(2.0, 4.0 * len(agents) / max(max_cc, 1))
    clock = DecisionClock(
        decision_tick=decision_tick,
        reference_tick=sim.get("reference_decision_tick", 5.0),
        max_concurrency=max_cc,
    )
    sp = cfg["labels"].get("sensory_prompts", {})
    if "auditory" in sp:
        sp["auditory"]["window_seconds"] = int(clock.speech_window)
    print(f"  DecisionClock: tick={clock.decision_tick:.1f}s "
          f"speech_window={int(clock.speech_window)}s scale={clock.scale:.2f}", flush=True)

    from core.director import Director
    from gateway import WorldGateway
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

    # ── Dashboard emitter ──
    dash_emit = None
    dash_task = None
    if getattr(args, 'dashboard_port', 0):
        from dashboard.emitter import DashboardEmitter
        from dashboard.server import start_dashboard
        dash_emitter = DashboardEmitter()
        dash_emit = dash_emitter.emit
        dash_task = asyncio.create_task(start_dashboard(dash_emitter, args.dashboard_port))

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
                         trace_fn=tracer.callback(), director=director,
                         dashboard_emit=dash_emit)

    if api_task:
        api_server.should_exit = True
        api_task.cancel()
        try:
            await api_task
        except (asyncio.CancelledError, Exception):
            pass
    if dash_task:
        dash_task.cancel()
        try:
            await dash_task
        except (asyncio.CancelledError, Exception):
            pass

    elapsed = time.time() - t_start
    gate_stats = {pname: gate.stats() for pname, gate in cfg["concurrency_gates"].items()}
    tracer.set_meta({"gate_stats": gate_stats,
                     "telemetry": cfg["telemetry"].stats(),
                     "clock": {"decision_tick": round(clock.decision_tick, 2),
                               "scale": round(clock.scale, 3)}})
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

    from loop import run_agent
    print(f"Agent: {agent.name} | personality: {agent.get('agent').personality}")
    print(f"{'='*50}")

    await run_agent(agent, world, brain, cfg["assembler"],
                    systems,
                    runtime=30, cfg=loop_cfg,
                    trace_fn=lambda t: print(
                        f"  [{agent.name}] → {t.get('target','?')} | "
                        f"{t.get('action_text','?')[:80]}"))


def cmd_validate_config(args):
    """Validate world.yaml + prompts.yaml schema without running agents."""
    errors = []
    cfg = load_config(args.world or None)
    world = cfg["world"]

    for key in ["world", "zones", "entities"]:
        if key not in world:
            errors.append(f"world.yaml missing key: {key}")

    for e in world.get("entities", []):
        if "id" not in e:
            errors.append(f"Entity missing id")
        if "zone" not in e:
            errors.append(f"Entity '{e.get('name', e.get('id', '?'))}' missing zone")

    loader = cfg["assembler"].loader
    all_slots = loader.data.get("slots", {})
    for tpl_name, tpl in loader.data.get("templates", {}).items():
        for slot_name in tpl.get("slots", []):
            if slot_name not in all_slots:
                errors.append(f"Template '{tpl_name}' references undefined slot '{slot_name}'")

    known_ctx = {"main_thread", "name", "personality", "drives_table", "delta_text",
                 "zone_name", "sensory_text", "memory_text", "messages_text",
                 "interactable_text", "visible_text", "hearing_text", "round",
                 "caller_name", "caller_id", "target_name", "target_id",
                 "gate_text", "item_narrative", "state_description",
                 "conversation_text", "traits_text", "drive_boundaries",
                 "last_intent", "last_target",
                 "conversation_since_last_action", "drive_delta_since_last_action"}
    for slot_name, slot in all_slots.items():
        cond = slot.get("condition", "")
        if cond and cond not in known_ctx:
            errors.append(f"Slot '{slot_name}' has unknown condition '{cond}' (not in known ctx keys)")

    sp = loader.data.get("sensory_prompts", {})
    for ch_name in sp:
        if "header" not in sp[ch_name]:
            errors.append(f"sensory_prompts.{ch_name} missing 'header'")

    if errors:
        print(f"\u274c Config validation FAILED ({len(errors)} issues):")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"\u2705 Config validation PASSED")
        zones = len(world.get("zones", []))
        entities = len(world.get("entities", []))
        agents = sum(1 for e in world.get("entities", []) if "agent" in e)
        print(f"   {zones} zones, {entities} entities, {agents} agents")
        print(f"   {len(all_slots)} slots defined, {len(loader.data.get('templates', {}))} templates")
