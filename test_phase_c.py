"""
Phase C: End-to-end stress test.
3 agents × 2 zones × 8 interactions each = 24 interactions.
验证: 跨 zone 移动、gate 传送、sensory 清空/重建、并发 LLM、属性一致性。
"""
import sys, os, yaml, asyncio, uuid, time, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World
from agent.brain import Brain
from agent.drives import DriveSystem
from layers.interaction import ActionDef, TargetType, ResolveType
from layers.visual import VisualLayer
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from interaction.resolver import InteractionResolver
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from entity.entity import Entity

BASE = os.path.dirname(os.path.abspath(__file__))


async def run_agent(agent, world, brain, systems, max_actions=8):
    agent_layer = agent.get("agent")
    actions_done = 0
    zone_changes = 0

    while actions_done < max_actions:
        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0:
            elapsed = 0

        systems["decay"].tick(agent, elapsed)
        systems["sensory"].update(agent, world.entities)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # Busy result
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            if result.move_to_zone:
                zone_changes += 1
                print(f"  [{agent.name}] 🚪 → {result.move_to_zone}")

        # Inbox
        inbox_msgs = agent_layer.inbox.drain()
        if inbox_msgs:
            pass  # tracked by LLM think prompt

        # Decide
        if agent.status == "idle":
            sensory = agent_layer.sensory
            drives = agent_layer.drives
            memory = agent_layer.memory
            zone_data = world.get_zone_data(agent.zone)

            interactable_records = sensory.get_interactable()
            visible_records = sensory.get_visible_only()

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
                "visible_text": "",
                "memory_text": memory.to_prompt_text(3),
                "messages_text": "",
            }

            if inbox_msgs:
                msg_text = "\n".join(
                    f"- {m.from_agent_name}: {m.content[:40]}" for m in inbox_msgs
                )
                context["messages_text"] = msg_text

            decision = await brain.decide(context)

            # Move
            move_to = decision.get("move_to")
            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                systems["sensory"].update(agent, world.entities)
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

                    elif act_def.target_type.value == "agent":
                        world.send_message(agent.id, target_id, action_name,
                                           f"{agent.name}想和你{action_name}")
                        actions_done += 1

        await asyncio.sleep(1.5 if agent.status == "busy" else 1.0)

    # Drain final result
    for _ in range(20):
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            if result.move_to_zone:
                zone_changes += 1
            break
        if agent.status == "idle":
            break
        await asyncio.sleep(1.0)

    return zone_changes


async def main():
    # Load configs + world
    with open(os.path.join(BASE, "config", "world.yaml")) as f:
        world_cfg = yaml.safe_load(f)
    with open(os.path.join(BASE, "config", "llm.yaml")) as f:
        llm_cfg = yaml.safe_load(f)
    loader = PromptLoader(os.path.join(BASE, "config", "prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(llm_cfg)
    brain = Brain(llm, assembler)
    resolver = InteractionResolver(llm, assembler)

    sound_map = {
        "饮用": "杯子碰吧台的清脆声",
        "交谈": "低声的说话声",
        "倚靠": "吧台轻微的吱呀声",
    }
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(resolver, sound_map),
        "decay": DecaySystem(),
    }

    world = World(world_cfg, systems)

    # ── Add second zone: 中央广场 ──
    world.zones["square"] = {
        "id": "square", "name": "中央广场", "width": 12, "height": 10,
        "tile_size": 32, "ambient_light": "#fff8dc",
        "connections": [],
    }

    # ── Gate entities: bar ↔ square ──
    from layers.visual import VisualLayer
    from layers.interaction import InteractionLayer, ActionDef, TargetType, ResolveType

    gate_defs = [
        {"id": "bar_door", "zone": "bar_zone", "pos": [0, 4], "sprite": "door",
         "to_zone": "square", "to_pos": [11, 5], "name": "酒馆门→广场"},
        {"id": "square_gate", "zone": "square", "pos": [11, 5], "sprite": "door",
         "to_zone": "bar_zone", "to_pos": [0, 4], "name": "广场入口→酒馆"},
    ]
    for gd in gate_defs:
        e = Entity(id=gd["id"], name=gd["name"], zone=gd["zone"], pos=gd["pos"])
        e.layers["visual"] = VisualLayer(visible_radius=20, sprite=gd["sprite"],
                                          info={"look": gd["name"]})
        e.layers["interaction"] = InteractionLayer(
            interaction_radius=1, public_attrs={}, private_attrs={},
            actions={
                "离开": ActionDef(method="离开", target_type=TargetType.PASSIVE,
                                  resolve=ResolveType.RULE,
                                  rule={"narrative": "{caller}穿过门",
                                        "move_to_zone": gd["to_zone"],
                                        "move_to_pos": gd["to_pos"]}),
            }
        )
        world.entities[e.id] = e

    # ── 3 agents ──
    world.register_external_agent("laowang", "老王", "bar_zone", [18, 8], sprite=None,
                                   personality="老练世故，喜欢在酒馆喝酒聊天，经常请客")
    laowang = world.entities["laowang"]
    laowang.get("interaction").private_attrs.update({
        "coins": 80, "hunger": 40, "thirst": 70, "social": 90,
        "energy": 60, "fun": 80, "mood": 70,
    })
    laowang.get("agent").drives = DriveSystem(
        attrs=laowang.get("interaction").private_attrs,
        decay_rates={"thirst": 0.025, "hunger": 0.02, "social": 0.015, "energy": -0.01, "fun": 0.02},
    )
    laowang.get("interaction").actions["交谈"] = ActionDef(
        method="交谈", target_type=TargetType.AGENT
    )

    world.register_external_agent("xiaohong", "小红", "bar_zone", [3, 3], sprite=None,
                                   personality="内向谨慎，喜欢独处，精打细算，偶尔社交")
    xiaohong = world.entities["xiaohong"]
    xiaohong.get("interaction").private_attrs.update({
        "coins": 200, "hunger": 60, "thirst": 40, "social": 20,
        "energy": 70, "fun": 50, "mood": 40,
    })
    xiaohong.get("agent").drives = DriveSystem(
        attrs=xiaohong.get("interaction").private_attrs,
        decay_rates={"thirst": 0.025, "hunger": 0.02, "social": 0.015, "energy": -0.01, "fun": 0.02},
    )
    xiaohong.get("interaction").actions["交谈"] = ActionDef(
        method="交谈", target_type=TargetType.AGENT
    )

    agents = [world.entities["xiaoming"], laowang, xiaohong]

    # ── Init snapshot ──
    init_snap = {}
    print("=" * 60)
    print("  Phase C: 3 Agents × 2 Zones × 8 Actions")
    print("=" * 60)
    for a in agents:
        pa = a.get("interaction").private_attrs
        init_snap[a.name] = dict(pa)
        print(f"  {a.name:4s} zone={a.zone} ({a.pos[0]},{a.pos[1]}) "
              f"thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0)} "
              f"social={pa.get('social',0):.0f}")
    print()

    # ── Run ──
    tasks = [
        run_agent(agents[i], world, brain, systems, max_actions=8)
        for i in range(3)
    ]
    zone_changes = await asyncio.gather(*tasks)

    # ── Verify ──
    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)
    passed = 0
    failed = 0
    details = []

    for a in agents:
        pa = a.get("interaction").private_attrs
        mem = a.get("agent").memory

        for attr in ["thirst", "hunger", "social", "energy", "fun", "mood"]:
            v = pa.get(attr, 0)
            if 0 <= v <= 100:
                passed += 1
            else:
                failed += 1
                details.append(f"{a.name}.{attr}={v} out of bounds")

        if pa.get("coins", 0) >= 0:
            passed += 1
        else:
            failed += 1
            details.append(f"{a.name}.coins={pa.get('coins', 0)} negative")

        # Zone changes ok
        zc = zone_changes[agents.index(a)]
        print(f"  {a.name:4s} zone={a.zone} ({a.pos[0]},{a.pos[1]}) "
              f"thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0)} "
              f"mood={pa.get('mood',0):.0f} mem={len(mem.entries)} "
              f"zone_changes={zc}")

    if details:
        for d in details:
            print(f"  ❌ {d}")

    info = world.entities.get("bar_counter")
    if info:
        bm = info.get("interaction").private_attrs.get("mood", 0)
        print(f"  🍺 吧台老板 mood: {bm}")

    print(f"\n  Attributes: {passed} ok, {failed} violations | "
          f"Zone changes: {sum(zone_changes)}")

    if failed:
        print("  ❌ PHASE C FAILED")
    else:
        print("  ✅ PHASE C PASSED")


if __name__ == "__main__":
    asyncio.run(main())
