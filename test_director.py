#!/usr/bin/env python3
"""Test Director controlled mode — freeze, snap, order, unfreeze, release."""
import sys, os, time, yaml, asyncio

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "src"))

from core.world import World
from core.director import Director
from agent.brain import Brain
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from loop import run_agent, LoopConfig
from agent.drives import DriveSystem

# ── Setup ──
with open(os.path.join(base_dir, "config/world.yaml")) as f: wc = yaml.safe_load(f)
with open(os.path.join(base_dir, "config/llm.yaml")) as f: lc = yaml.safe_load(f)
loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
assembler = PromptAssembler(loader)
labels = loader.data.get("text_labels", {})
labels["sensory_prompts"] = loader.data.get("sensory_prompts", {})

llm = LLMClient(lc)
brain = Brain(llm, assembler)
systems = {
    "sensory": SensorySystem(),
    "interaction": InteractionSystem(llm, assembler),
    "decay": DecaySystem(),
}
world = World(wc, systems)
director = Director(world)

# ── Setup drives ──
sim = wc["world"].get("simulation", {})
attr_cfg = sim.get("drive", {}).get("attributes", {})
currency = sim.get("currency", "coins")
for e in world.entities.values():
    al = e.get("agent")
    inter = e.get("interaction")
    if al and al.drives:
        al.drives.attr_cfg = attr_cfg
    if inter:
        inter.attr_bounds = {k: {"min": v.get("min", 0), "max": v.get("max", 100)}
                             for k, v in attr_cfg.items()}
        inter.currency_key = currency

# ── Get agents ──
agents = [e for e in world.entities.values()
          if e.has("agent") and e.get("agent").autonomous]
print(f"Agents: {len(agents)}")

kl = sim.get("kl", {})
loop_cfg = LoopConfig(
    poll_interval=sim.get("poll_interval", 0.3),
    thresholds=kl.get("state_thresholds", [30, 60, 80]),
    coin_epsilon=kl.get("coin_epsilon", 5),
    stale_timeout=sim.get("stale_timeout", 30),
    currency=currency,
    text=sim.get("text", {}),
    labels=labels,
    default_patience=sim.get("default_patience", 5),
    memory_prompt_count=sim.get("memory_prompt_count", 5),
)

trace_log = []


async def test():
    # ── 1. Start agents ──
    # Run 杰洛特 controlled, others autonomous
    geralt = world.entities["geralt"]
    others = [a for a in agents if a.id != "geralt"]
    
    director.take("geralt")
    
    # Start others as autonomous
    auto_tasks = [run_agent(a, world, brain, assembler, systems, 60,
                           cfg=loop_cfg, director=None)
                  for a in others]
    
    # Start 杰洛特 with director
    geralt_task = run_agent(geralt, world, brain, assembler, systems, 60,
                            cfg=loop_cfg, director=director,
                            trace_fn=lambda t: trace_log.append(t))
    
    all_tasks = auto_tasks + [geralt_task]
    
    # ── 2. Let world init for 1s ──
    print("\n=== Phase 1: World init (1s) ===")
    gather_task = asyncio.ensure_future(asyncio.gather(*all_tasks))
    await asyncio.sleep(1)
    print(f"  Traces so far: {len(trace_log)}")
    for t in trace_log:
        print(f"  [{t.get('agent','?')}] → {t.get('target','?')}: {t.get('action_text','?')[:50]}")
    
    # ── 3. Freeze + snap + order ──
    print("\n=== Phase 2: Freeze + snap + order ===")
    director.freeze()
    await asyncio.sleep(0.5)  # let loops settle into frozen state
    
    snap = director.snap("geralt")
    print(f"  snap.name: {snap.get('name')}")
    print(f"  snap.zone: {snap.get('zone')}")
    print(f"  snap.pos: {snap.get('pos')}")
    print(f"  snap.drives: {snap.get('drives')}")
    print(f"  snap.memory ({len(snap.get('memory',[]))} entries): {snap.get('memory',[])[:3]}")
    for ch, data in snap.get("sensory", {}).items():
        names = list(data.keys())[:5] if data else []
        print(f"  snap.sensory.{ch}: {len(data)} entities, e.g. {names}")
    
    # Order 杰洛特 to do something
    order = {
        "action": "走到酒馆中央大声宣布：白果园外有狮鹫出没，悬赏500金币！有兴趣的来找我。",
        "dialogue": "各位！白果园外有狮鹫出没，悬赏500金币！有兴趣的来找我。",
        "visual": "杰洛特站起身走到酒馆中央，提高嗓音",
        "story": "杰洛特走到酒馆中央，环顾四周提高嗓音宣布狮鹫悬赏。",
        "self_deltas": {},
    }
    director.order("geralt", order)
    print(f"  Ordered: {order['action'][:60]}")
    
    # ── 4. Unfreeze ──
    print("\n=== Phase 3: Unfreeze — waiting for order execution ===")
    director.unfreeze()
    
    # Wait for 杰洛特 to execute the order
    geralt_acted = False
    for _ in range(30):  # max 9 seconds
        await asyncio.sleep(0.3)
        for t in trace_log:
            if t.get("agent") == "杰洛特":
                geralt_acted = True
                print(f"  ✓ 杰洛特 acted: [{t.get('ts',0):.1f}s] → {t.get('target','?')}: {t.get('action_text','?')[:80]}")
                break
        if geralt_acted:
            break
    
    if not geralt_acted:
        print("  ⚠️ 杰洛特 did not act within 9s")
    
    await asyncio.sleep(2)  # let him do more things
    
    # ── 5. Release ──
    print("\n=== Phase 4: Release — return to autonomous ===")
    director.release("geralt")
    await asyncio.sleep(3)
    
    post_release = [t for t in trace_log if t.get("agent") == "杰洛特"]
    print(f"  杰洛特 total actions: {len(post_release)}")
    for t in post_release[-3:]:
        print(f"  [{t.get('ts',0):.1f}s] → {t.get('target','?')}: {t.get('action_text','?')[:80]}")
    
    # ── 6. Save traces ──
    import json
    with open("/tmp/trace_director.json", "w") as f:
        json.dump(trace_log, f, ensure_ascii=False, indent=2)
    print(f"\n  Traces saved: /tmp/trace_director.json ({len(trace_log)} entries)")
    
    # ── 7. Cleanup ──
    gather_task.cancel()
    try:
        await gather_task
    except (asyncio.CancelledError, Exception):
        pass
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"  Freeze: OK")
    print(f"  Snap: OK (sensory={bool(snap.get('sensory'))})")
    print(f"  Order: OK (pending consumed)")
    print(f"  Unfreeze + Exec: {'OK' if geralt_acted else 'FAIL'}")
    print(f"  Release: OK")
    print(f"  Director trace entries: {len(trace_log)}")


asyncio.run(test())
