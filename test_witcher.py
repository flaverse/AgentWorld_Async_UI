"""Witcher World Test: 3 zones × 3 NPCs (杰洛特, 叶奈法, 丹德里恩)."""
import sys, os, yaml, asyncio, uuid
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


async def run_npc(agent, world, brain, systems, max_actions=4):
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

        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            if result.move_to_zone:
                zone_changes += 1
                print(f"  [{agent.name}] 🚪 → {result.move_to_zone}")

        inbox_msgs = agent_layer.inbox.drain()

        if agent.status == "idle":
            sensory = agent_layer.sensory
            drives = agent_layer.drives
            memory = agent_layer.memory
            zone_data = world.get_zone_data(agent.zone)

            interactable_names = [r.name for r in sensory.get_interactable()]
            visible_names = [r.name for r in sensory.get_visible_only()]
            print(f"\n  [{agent.name}] 📍 {world.zones[agent.zone]['name']} ({agent.pos[0]},{agent.pos[1]}) | "
                  f"thirst={drives.attrs.get('thirst',0):.0f} "
                  f"coins={agent.get('interaction').private_attrs.get('coins',0)}")
            print(f"    附近: {interactable_names}")
            if visible_names:
                print(f"    看得见: {visible_names}")

            # Build context
            visible_text = ""
            if sensory.get_visible_only():
                visible_text = "\n".join(
                    f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | dist={r.distance}"
                    for r in sensory.get_visible_only()
                )
            messages_text = ""
            if inbox_msgs:
                messages_text = "\n".join(
                    f"- {m.from_agent_name}: \"{m.content[:50]}\"" for m in inbox_msgs
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
                "messages_text": messages_text,
                "hearing_text": sensory.to_prompt_hearing(),
            }

            decision = await brain.decide(context)

            # Move
            move_to = decision.get("move_to")
            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                print(f"     🚶 → ({move_to[0]},{move_to[1]})")
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
                            print(f"     🎯 {action_name} {target.name}")

                    elif act_def.target_type.value == "agent":
                        world.send_message(agent.id, target_id, action_name,
                                           f"{agent.name}想和你{action_name}")
                        actions_done += 1
                        print(f"     💬 {action_name} → {target.name}")

            # Reply
            reply_to = decision.get("respond_to")
            reply_text = decision.get("reply")
            if reply_to and reply_text:
                world.send_message(agent.id, reply_to, "reply", reply_text)

        await asyncio.sleep(2.0 if agent.status == "busy" else 1.5)

    # Drain final
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
        "interaction": InteractionSystem(resolver, {"饮用": "杯子碰吧台声", "交谈": "说话声"}),
        "decay": DecaySystem(),
    }

    world = World(world_cfg, systems)

    print("=" * 60)
    print("  猎魔人世界 — 白果园")
    print("=" * 60)
    print(f"  Zones: {list(world.zones.keys())}")
    print(f"  Entities: {len(world.entities)}")
    for zid, z in world.zones.items():
        ents = [e for e in world.entities.values() if e.zone == zid]
        names = [e.name for e in ents]
        print(f"    {z['name']} ({len(ents)}): {names}")
    print()

    agents = [e for e in world.entities.values()
              if e.get("agent") and e.get("agent").autonomous]
    print(f"  NPCs: {[a.name for a in agents]}")
    for a in agents:
        pa = a.get("interaction").private_attrs
        print(f"    {a.name} in {world.zones[a.zone]['name']} ({a.pos[0]},{a.pos[1]}) "
              f"thirst={pa.get('thirst',0):.0f} social={pa.get('social',0):.0f} "
              f"coins={pa.get('coins',0)}")
    print()

    # Run
    tasks = [run_npc(a, world, brain, systems, max_actions=5) for a in agents]
    zone_changes = await asyncio.gather(*tasks)

    # Verify
    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)
    passed = 0
    failed = 0

    for a in agents:
        pa = a.get("interaction").private_attrs
        mem = a.get("agent").memory
        for attr in ["thirst", "hunger", "social", "energy", "fun", "mood"]:
            v = pa.get(attr, 0)
            if 0 <= v <= 100:
                passed += 1
            else:
                failed += 1
                print(f"  ❌ {a.name}.{attr}={v}")
        if pa.get("coins", 0) >= 0:
            passed += 1
        else:
            failed += 1
            print(f"  ❌ {a.name}.coins={pa.get('coins', 0)}")

        zc = zone_changes[agents.index(a)]
        print(f"  {a.name:4s} zone={a.zone:8s} ({a.pos[0]},{a.pos[1]}) "
              f"thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0)} "
              f"mood={pa.get('mood',0):.0f} mem={len(mem.entries)} zc={zc}")

    print(f"\n  Attributes: {passed} ok, {failed} violations")
    if failed:
        print("  ❌ FAILED")
    else:
        print("  ✅ PASSED")


if __name__ == "__main__":
    asyncio.run(main())
