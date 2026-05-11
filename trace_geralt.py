"""Verbose single-agent trace for Geralt."""
import sys, os, yaml, asyncio, uuid, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World
from agent.brain import Brain
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from interaction.resolver import InteractionResolver
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem

BASE = os.path.dirname(os.path.abspath(__file__))


async def trace_geralt():
    with open(os.path.join(BASE, "config/world.yaml")) as f:
        world_cfg = yaml.safe_load(f)
    with open(os.path.join(BASE, "config/llm.yaml")) as f:
        llm_cfg = yaml.safe_load(f)

    loader = PromptLoader(os.path.join(BASE, "config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(llm_cfg)
    brain = Brain(llm, assembler)
    resolver = InteractionResolver(llm, assembler)
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(resolver, {"饮用": "杯子碰吧台声", "交谈": "说话声"}),
        "decay": DecaySystem(),
    }

    world = World(world_cfg, systems)
    agent = world.entities["geralt"]
    agent_layer = agent.get("agent")
    pa = agent.get("interaction").private_attrs

    print("=" * 70)
    print(f"  杰洛特  |  zone={agent.zone} ({agent.pos[0]},{agent.pos[1]})")
    print("=" * 70)
    print(f"初始化: thirst={pa['thirst']:.0f} hunger={pa['hunger']:.0f} coins={pa['coins']} "
          f"social={pa['social']:.0f} energy={pa['energy']:.0f} fun={pa['fun']:.0f}")
    print()

    for action_num in range(5):
        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0:
            elapsed = 0
        systems["decay"].tick(agent, elapsed)
        systems["sensory"].update(agent, world.entities)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # Busy result
        if agent.busy_result is not None:
            r = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(r, agent, world)
            if r.move_to_zone:
                print(f"  🚪 传送至 {r.move_to_zone}")
            print(f"  📖 结果: {r.narrative}")
            print(f"     我方: {r.caller_deltas}")
            if r.ambient_effects:
                print(f"     周边: {r.ambient_effects}")
            print()

        if agent.status != "idle":
            await asyncio.sleep(2.0)
            continue

        sensory = agent_layer.sensory
        drives = agent_layer.drives
        memory = agent_layer.memory
        zone_data = world.get_zone_data(agent.zone)
        pa = agent.get("interaction").private_attrs

        print(f"─── 第 {action_num + 1} 次决策 ───")
        print(f"位置: {world.zones[agent.zone]['name']} ({agent.pos[0]},{agent.pos[1]})")
        print(f"状态: thirst={pa['thirst']:.0f} hunger={pa['hunger']:.0f} coins={pa['coins']} "
              f"social={pa['social']:.0f} energy={pa['energy']:.0f} fun={pa['fun']:.0f}")
        print()

        # What Geralt sees
        for r in sensory.get_interactable():
            print(f"  ✅ {r.name} ({r.pos[0]},{r.pos[1]}) actions={r.actions}")
        for r in sensory.get_visible_only():
            print(f"  👁️ {r.name} ({r.pos[0]},{r.pos[1]}) dist={r.distance}")
        print()

        # Build prompt
        visible_text = ""
        if sensory.get_visible_only():
            visible_text = "\n".join(
                f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | dist={r.distance}"
                for r in sensory.get_visible_only()
            )

        context = {
            "round": action_num + 1,
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

        full_prompt = assembler.assemble("agent_decision", context)
        print("=== LLM #1 PROMPT START ===")
        print(full_prompt)
        print("=== LLM #1 PROMPT END ===")
        print()

        decision = await brain.decide(context)
        print(f"🆔 Decision JSON: {json.dumps(decision, ensure_ascii=False)}")
        print()

        move_to = decision.get("move_to")
        if move_to and isinstance(move_to, list) and len(move_to) == 2:
            agent.move_to(move_to)
            agent.last_action_time = world.clock.now()
            print(f"  🚶 移至 ({move_to[0]},{move_to[1]})")
            systems["sensory"].update(agent, world.entities)
            systems["interaction"].update_sensory(agent, world.entities)
            print()

        target_id = decision.get("target_entity")
        action_name = decision.get("action")
        if target_id and action_name and target_id in world.entities:
            target = world.entities[target_id]
            il = target.get("interaction")
            if il and il.get_action(action_name):
                ad = il.get_action(action_name)
                if ad.target_type.value == "passive":
                    if systems["interaction"].can_interact(agent, target):
                        if ad.resolve.value == "llm":
                            amb = world.get_ambient_entities(target, radius=2, exclude={agent.id})
                            print(f"  🔍 裁判视野 (周边实体):")
                            for a in amb:
                                print(f"      {a['name']} dist={a['distance']} | {json.dumps(a['private_hint'], ensure_ascii=False)}")
                        iid = uuid.uuid4().hex[:8]
                        systems["interaction"].submit(iid, agent, target, action_name, world)
                        agent.last_action_time = world.clock.now()
                        print(f"  🎯 {action_name} → {target.name} (busy...)")
                        print()
                elif ad.target_type.value == "agent":
                    world.send_message(agent.id, target_id, action_name, f"{agent.name}想和你{action_name}")
                    print(f"  💬 {action_name} → {target.name}")
                    print()

        await asyncio.sleep(2.5)

    print("=" * 70)
    print("  最终状态")
    print("=" * 70)
    pa = agent.get("interaction").private_attrs
    print(f"thirst={pa['thirst']:.0f} hunger={pa['hunger']:.0f} coins={pa['coins']} "
          f"social={pa['social']:.0f} energy={pa['energy']:.0f} fun={pa['fun']:.0f} mood={pa['mood']:.0f}")
    print()
    print("记忆:")
    for e in agent_layer.memory.entries:
        print(f"  {e.get('narrative', '?')}")


if __name__ == "__main__":
    asyncio.run(trace_geralt())
