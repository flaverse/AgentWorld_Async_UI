"""
Phase C verbose: Full agent input/output trace.
"""
import sys, os, yaml, asyncio, uuid, time, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World
from agent.brain import Brain
from agent.drives import DriveSystem
from layers.interaction import ActionDef, TargetType, ResolveType
from layers.visual import VisualLayer
from layers.interaction import InteractionLayer
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from interaction.resolver import InteractionResolver
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from entity.entity import Entity

BASE = os.path.dirname(os.path.abspath(__file__))


async def run_agent_verbose(agent, world, brain, assembler, systems, name, max_actions=3):
    """Verbose agent loop: prints full prompt + decision + result."""
    agent_layer = agent.get("agent")
    actions_done = 0

    print(f"\n{'#'*70}")
    print(f"#  {name} 启动  |  zone={agent.zone} pos=({agent.pos[0]},{agent.pos[1]})")
    inter = agent.get("interaction")
    pa = inter.private_attrs
    print(f"#  thirst={pa['thirst']:.0f} hunger={pa['hunger']:.0f} coins={pa['coins']} social={pa['social']:.0f} energy={pa['energy']:.0f} fun={pa['fun']:.0f}")
    print(f"{'#'*70}")

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
            print(f"\n─── 📖 交互结果 ───")
            print(f"  叙事: {result.narrative}")
            print(f"  我方变化: {result.caller_deltas}")
            print(f"  目标变化: {result.target_deltas}")
            if result.ambient_effects:
                print(f"  周边影响: {result.ambient_effects}")
            print(f"  状态: thirst={pa['thirst']:.0f} coins={pa['coins']} mood={pa['mood']:.0f}")

        # Inbox
        inbox_msgs = agent_layer.inbox.drain()
        if inbox_msgs:
            for m in inbox_msgs:
                print(f"\n─── 📬 收到消息 ───")
                print(f"  来自: {m.from_agent_name}  |  内容: {m.content[:60]}")

        # Decide
        if agent.status == "idle":
            sensory = agent_layer.sensory
            drives = agent_layer.drives
            memory = agent_layer.memory
            zone_data = world.get_zone_data(agent.zone)

            interactable_text = sensory.to_prompt_vision()

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
                "interactable_text": interactable_text,
                "visible_text": "",
                "memory_text": memory.to_prompt_text(3),
                "messages_text": "",
            }

            if inbox_msgs:
                msg_text = "\n".join(
                    f"- {m.from_agent_name}: {m.content[:40]}" for m in inbox_msgs
                )
                context["messages_text"] = msg_text

            # Build actual prompt
            prompt = assembler.assemble("agent_decision", context)

            print(f"\n─── 🤔 Decison #{actions_done+1} ───")
            print(f"─── 状态: thirst={pa['thirst']:.0f} coins={pa['coins']} mood={pa['mood']:.0f} pos=({agent.pos[0]},{agent.pos[1]})")
            print(f"─── 感受到的实体:")
            for r in sensory.get_interactable():
                print(f"      {r.name} id={r.entity_id} pos={r.pos} actions={r.actions}")
            for r in sensory.get_visible_only():
                print(f"      ({r.name} id={r.entity_id} pos={r.pos} dist={r.distance})")

            decision = await brain.decide(context)
            print(f"─── 决策 ───")
            print(f"  thinking: {decision.get('thinking','')[:120]}")
            print(f"  move_to: {decision.get('move_to')}")
            print(f"  target_entity: {decision.get('target_entity')}")
            print(f"  action: {decision.get('action')}")

            # Move
            move_to = decision.get("move_to")
            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                dist = agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                print(f"─── 🚶 移动 ───")
                print(f"  ({agent.pos[0]},{agent.pos[1]}) 耗时 {dist} 分钟")
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
                    print(f"─── 🔧 执行交互 ───")
                    print(f"  目标: {target.name} ({target_id})")
                    print(f"  动作: {action_name}")
                    print(f"  target_type: {act_def.target_type.value}")
                    print(f"  resolve: {act_def.resolve.value}")

                    if act_def.target_type.value == "passive":
                        if systems["interaction"].can_interact(agent, target):
                            # Show resolver ambient context
                            if act_def.resolve.value == "llm":
                                ambient = world.get_ambient_entities(target, radius=2, exclude={agent.id})
                                print(f"  周边实体 (进入裁判视野):")
                                for ae in ambient:
                                    print(f"    - {ae['name']} dist={ae['distance']} | {json.dumps(ae['private_hint'], ensure_ascii=False)}")

                            iid = uuid.uuid4().hex[:8]
                            systems["interaction"].submit(iid, agent, target, action_name, world)
                            agent.last_action_time = world.clock.now()
                            actions_done += 1
                            print(f"  → 已提交, agent busy, 等待裁定...")

                    elif act_def.target_type.value == "agent":
                        world.send_message(agent.id, target_id, action_name,
                                           f"{agent.name}想和你{action_name}")
                        actions_done += 1
                        print(f"  → 已发送 inbox 消息")

        await asyncio.sleep(2.0)

    # Drain final
    for _ in range(20):
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            print(f"\n─── 📖 最终裁定结果 ───")
            print(f"  叙事: {result.narrative}")
            print(f"  我方变化: {result.caller_deltas}")
            break
        if agent.status == "idle":
            break
        await asyncio.sleep(1.0)

    print(f"\n=== {name} 结束 === thirst={pa['thirst']:.0f} coins={pa['coins']} mood={pa['mood']:.0f}")


async def main():
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

    # ── Add second zone + gates ──
    world.zones["square"] = {
        "id": "square", "name": "中央广场", "width": 12, "height": 10,
        "tile_size": 32, "ambient_light": "#fff8dc", "connections": [],
    }

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

    # ── Register 老王 ──
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
    laowang.get("interaction").actions["交谈"] = ActionDef(method="交谈", target_type=TargetType.AGENT)

    # ── Register 小红 ──
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
    xiaohong.get("interaction").actions["交谈"] = ActionDef(method="交谈", target_type=TargetType.AGENT)

    # ── Run sequentially (not concurrent) for clear output ──
    agents = [
        ("小明", world.entities["xiaoming"]),
        ("老王", laowang),
        ("小红", xiaohong),
    ]

    for label, a in agents:
        await run_agent_verbose(a, world, brain, assembler, systems, label, max_actions=3)


if __name__ == "__main__":
    asyncio.run(main())
