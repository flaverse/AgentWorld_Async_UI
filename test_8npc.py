#!/usr/bin/env python3
"""
8 NPCs × 3 zones — Endurance Test Runner.
Runs all agents concurrently, logs everything, generates report.
"""
import sys, os, yaml, asyncio, uuid, json, time, logging
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World
from agent.brain import Brain
from agent.drives import DriveSystem
from layers.interaction import ActionDef, TargetType, ResolveType
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from interaction.resolver import InteractionResolver
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE, "test_8npc_log.jsonl")
REPORT_FILE = os.path.join(BASE, "test_8npc_report.json")

# ═══════════════════════════════════════
# Structured logger
# ═══════════════════════════════════════
class TestLogger:
    def __init__(self):
        self.events = []
        self.start_time = time.time()
        self._lock = __import__('threading').Lock()

    def log(self, event_type: str, **kwargs):
        entry = {
            "ts": time.time() - self.start_time,
            "wall_time": datetime.now().isoformat(),
            "event": event_type,
            **kwargs,
        }
        with self._lock:
            self.events.append(entry)
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_summary(self):
        actions = [e for e in self.events if e["event"] == "action"]
        errors = [e for e in self.events if e["event"] == "error"]
        by_agent = defaultdict(int)
        zone_changes = 0
        for a in actions:
            by_agent[a.get("agent", "?")] += 1
            if a.get("zone_change"):
                zone_changes += 1
        return {
            "total_actions": len(actions),
            "total_errors": len(errors),
            "actions_by_agent": dict(by_agent),
            "zone_changes": zone_changes,
            "duration_seconds": time.time() - self.start_time,
        }

test_log = TestLogger()


# ═══════════════════════════════════════
# Agent runner
# ═══════════════════════════════════════
async def run_agent(agent, world, brain, systems, max_actions=4):
    agent_layer = agent.get("agent")
    actions_done = 0
    zone_changes = 0

    while actions_done < max_actions:
        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0:
            elapsed = 0

        systems["decay"].tick(agent, elapsed)
        systems["sensory"].update(agent, world.entities, world)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # Busy result
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            if result.move_to_zone:
                zone_changes += 1
            test_log.log("action_result",
                         agent=agent.name, agent_id=agent.id,
                         narrative=result.narrative[:120],
                         deltas=result.caller_deltas,
                         zone_change=bool(result.move_to_zone))

        # Inbox
        agent_layer.inbox.drain()

        # Decide
        if agent.status == "idle":
            sensory = agent_layer.sensory
            drives = agent_layer.drives
            memory = agent_layer.memory
            zone_data = world.get_zone_data(agent.zone)

            # Dump initial state
            pa = agent.get("interaction").private_attrs
            test_log.log("agent_state",
                         agent=agent.name, agent_id=agent.id,
                         zone=agent.zone, pos=list(agent.pos),
                         thirst=pa.get("thirst", 0), hunger=pa.get("hunger", 0),
                         coins=pa.get("coins", 0), social=pa.get("social", 0),
                         energy=pa.get("energy", 0), fun=pa.get("fun", 0),
                         mood=pa.get("mood", 0),
                         sees=[r.name for r in sensory.get_interactable()])

            visible_text = ""
            if sensory.get_visible_only():
                visible_text = "\n".join(
                    f"id={r.entity_id}|{r.name}|dist={r.distance}"
                    for r in sensory.get_visible_only()
                )

            context = {
                "round": actions_done + 1,
                "name": agent.name,
                "personality": agent_layer.personality,
                "drives_table": drives.to_prompt_table(),
                "zone_name": zone_data.get("name", agent.zone),
                "zone_width": zone_data.get("width", 10),
                "zone_height": zone_data.get("height", 10),
                "pos_x": agent.pos[0],
                "pos_y": agent.pos[1],
                "interactable_text": sensory.to_prompt_vision(),
                "visible_text": visible_text,
                "memory_text": memory.to_prompt_text(3),
                "messages_text": "",
                "hearing_text": sensory.to_prompt_hearing(),
            }

            try:
                decision = await brain.decide(context)
            except Exception as e:
                test_log.log("error", agent=agent.name, error=str(e), phase="think")
                await asyncio.sleep(2)
                continue

            # Move
            move_to = decision.get("move_to")
            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                systems["sensory"].update(agent, world.entities, world)
                systems["interaction"].update_sensory(agent, world.entities)

            # Interact
            target_id = decision.get("target_entity")
            action_name = decision.get("action")
            if target_id and action_name and target_id in world.entities:
                target = world.entities[target_id]
                inter_layer = target.get("interaction")
                if inter_layer and inter_layer.get_action(action_name):
                    act_def = inter_layer.get_action(action_name)

                    if act_def.target_type.value == "passive":
                        if systems["interaction"].can_interact(agent, target):
                            iid = uuid.uuid4().hex[:8]
                            systems["interaction"].submit(iid, agent, target, action_name, world)
                            agent.last_action_time = world.clock.now()
                            actions_done += 1
                            test_log.log("action",
                                         agent=agent.name, agent_id=agent.id,
                                         zone=agent.zone, pos=list(agent.pos),
                                         action=action_name,
                                         target=target.name, target_id=target_id,
                                         resolve=act_def.resolve.value)

                    elif act_def.target_type.value == "agent":
                        world.send_message(agent.id, target_id, action_name,
                                           f"{agent.name}想和你{action_name}")
                        actions_done += 1
                        test_log.log("action",
                                     agent=agent.name, agent_id=agent.id,
                                     action=action_name, target=target.name,
                                     target_type="agent")

        wait = 2.0 if agent.status == "busy" else 1.5
        await asyncio.sleep(wait)

    # Drain final result
    for _ in range(20):
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            if result.move_to_zone:
                zone_changes += 1
            test_log.log("action_result",
                         agent=agent.name, agent_id=agent.id,
                         narrative=result.narrative[:120],
                         deltas=result.caller_deltas,
                         zone_change=bool(result.move_to_zone))
            break
        if agent.status == "idle":
            break
        await asyncio.sleep(1.0)

    return zone_changes


# ═══════════════════════════════════════
# Extra NPCs definition
# ═══════════════════════════════════════
EXTRA_NPCS = [
    {"id": "vesemir",   "name": "维瑟米尔", "zone": "bar_zone", "pos": [20, 8],
     "personality": "狼学派最年长的猎魔人，杰洛特的导师。沉稳老练，偶尔来酒馆小酌。",
     "coins": 200, "thirst": 50, "hunger": 40, "social": 30, "energy": 60, "fun": 35, "mood": 55},
    {"id": "triss",     "name": "特莉丝",   "zone": "square",   "pos": [35, 15],
     "personality": "诺维格瑞的女术士，红发绿眼。正在寻找可靠的盟友对抗神殿审判。",
     "coins": 300, "thirst": 35, "hunger": 45, "social": 25, "energy": 75, "fun": 30, "mood": 50},
    {"id": "zoltan",    "name": "卓尔坦",   "zone": "bar_zone", "pos": [15, 10],
     "personality": "矮人商人，杰洛特的老朋友。嗓门大，爱喝酒，做生意精明。",
     "coins": 500, "thirst": 65, "hunger": 50, "social": 60, "energy": 55, "fun": 70, "mood": 70},
    {"id": "keira",     "name": "凯拉",     "zone": "herb_hut", "pos": [8, 3],
     "personality": "年轻的女术士，对炼金术和古籍充满热情。有点天真但学得快。",
     "coins": 150, "thirst": 30, "hunger": 55, "social": 15, "energy": 80, "fun": 45, "mood": 60},
    {"id": "lambert",   "name": "兰伯特",   "zone": "square",   "pos": [20, 10],
     "personality": "狼学派猎魔人，年轻气盛，说话刻薄但内心善良。刚完成一个委托回来。",
     "coins": 100, "thirst": 70, "hunger": 60, "social": 15, "energy": 70, "fun": 20, "mood": 40},
]


# ═══════════════════════════════════════
# Main
# ═══════════════════════════════════════
async def main():
    test_log.log("test_start", phase="init")

    with open(os.path.join(BASE, "config", "world.yaml")) as f:
        world_cfg = yaml.safe_load(f)
    with open(os.path.join(BASE, "config", "llm.yaml")) as f:
        llm_cfg = yaml.safe_load(f)

    loader = PromptLoader(os.path.join(BASE, "config", "prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(llm_cfg)
    brain = Brain(llm, assembler)
    resolver = InteractionResolver(llm, assembler)

    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(resolver),
        "decay": DecaySystem(),
    }

    world = World(world_cfg, systems)
    n_entities_start = len(world.entities)

    # Register extra NPCs
    for npc in EXTRA_NPCS:
        world.register_external_agent(
            agent_id=npc["id"], name=npc["name"],
            zone=npc["zone"], pos=npc["pos"],
            personality=npc["personality"]
        )
        e = world.entities[npc["id"]]
        e.get("interaction").private_attrs.update({
            k: v for k, v in npc.items()
            if k in ("coins", "hunger", "thirst", "social", "energy", "fun", "mood")
        })
        e.get("agent").drives = DriveSystem(
            attrs=e.get("interaction").private_attrs,
            decay_rates={"thirst": 0.022, "hunger": 0.018, "social": 0.015,
                         "energy": -0.01, "fun": 0.015},
        )

    agents = [world.entities[a] for a in
              ["geralt", "yennefer", "dandelion",
               "vesemir", "triss", "zoltan", "keira", "lambert"]]

    test_log.log("test_start",
                 agents=[a.name for a in agents],
                 n_entities=len(world.entities),
                 n_zones=len(world.zones))

    print("=" * 60)
    print(f"  8 NPC × 3 Zones Test | {len(agents)} agents | {len(world.entities)} entities")
    print("=" * 60)
    for a in agents:
        pa = a.get("interaction").private_attrs
        print(f"  {a.name:6s} {a.zone:10s} ({a.pos[0]:2d},{a.pos[1]:2d}) "
              f"thirst={pa['thirst']:.0f} coins={pa['coins']} social={pa['social']:.0f}")
    print()

    # Run all concurrently
    tasks = [run_agent(a, world, brain, systems, max_actions=4) for a in agents]
    zone_changes = await asyncio.gather(*tasks)

    # Wait for pending results
    print("\n等待最后裁定...")
    for _ in range(15):
        pending = any(a.busy_result is not None for a in agents if a.status == "busy")
        if not pending:
            break
        await asyncio.sleep(1)
        for a in agents:
            if a.busy_result is not None:
                r = a.busy_result
                a.busy_result = None
                systems["interaction"].apply_result(r, a, world)
                test_log.log("action_result", agent=a.name, narrative=r.narrative[:120])

    # ═══════════════════════════════════════
    # Generate Report
    # ═══════════════════════════════════════
    summary = test_log.get_summary()

    report = {
        "test": "8 NPC × 3 Zones Endurance",
        "generated": datetime.now().isoformat(),
        "summary": summary,
        "final_state": [],
        "attribute_checks": {"passed": 0, "failed": 0, "details": []},
    }

    print("\n" + "=" * 60)
    print("  Test Report")
    print("=" * 60)
    print(f"  Duration: {summary['duration_seconds']:.1f}s")
    print(f"  Total actions: {summary['total_actions']}")
    print(f"  Zone changes: {summary['zone_changes']}")
    print(f"  Errors: {summary['total_errors']}")
    print()

    for a in agents:
        pa = a.get("interaction").private_attrs
        mem = a.get("agent").memory
        actions = summary["actions_by_agent"].get(a.name, 0)

        # Attribute checks
        checks_ok = 0
        checks_fail = 0
        for attr in ["thirst", "hunger", "social", "energy", "fun", "mood"]:
            v = pa.get(attr, 0)
            if 0 <= v <= 100:
                checks_ok += 1
            else:
                checks_fail += 1
                report["attribute_checks"]["details"].append(
                    f"{a.name}.{attr}={v} out of bounds"
                )
        if pa.get("coins", 0) >= 0:
            checks_ok += 1
        else:
            checks_fail += 1

        report["attribute_checks"]["passed"] += checks_ok
        report["attribute_checks"]["failed"] += checks_fail

        print(f"  {a.name:6s} zone={a.zone:10s} actions={actions:2d} "
              f"thirst={pa['thirst']:.0f} coins={pa['coins']:.0f} "
              f"mood={pa['mood']:.0f} checks={checks_ok}/{checks_ok+checks_fail}")

        report["final_state"].append({
            "name": a.name, "zone": a.zone, "pos": list(a.pos),
            "actions": actions,
            "thirst": round(pa['thirst'], 1), "hunger": round(pa['hunger'], 1),
            "coins": round(pa['coins'], 1), "social": round(pa['social'], 1),
            "energy": round(pa['energy'], 1), "fun": round(pa['fun'], 1),
            "mood": round(pa['mood'], 1),
            "memory": [e.get("narrative", "")[:60] for e in mem.entries[:3]],
        })

    print()
    total = report["attribute_checks"]["passed"] + report["attribute_checks"]["failed"]
    print(f"  Attributes: {report['attribute_checks']['passed']}/{total} ok")

    if report["attribute_checks"]["failed"] > 0:
        print("  ❌ FAILED")
        for d in report["attribute_checks"]["details"]:
            print(f"    {d}")
    else:
        print("  ✅ PASSED")

    # Error report
    if summary["total_errors"] > 0:
        print(f"\n  ❌ {summary['total_errors']} errors occurred:")
        for e in test_log.events:
            if e["event"] == "error":
                print(f"    {e.get('agent','?')}: {e.get('error','')[:80]}")

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  Log: {LOG_FILE}")
    print(f"  Report: {REPORT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
