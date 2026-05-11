"""
Phase A: 3 agents concurrent in bar_zone.
验证: inbox 消息、并发 LLM、共享实体竞争、属性一致性。
"""
import sys, os, yaml, asyncio, uuid, time, json
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

# ── Metrics tracker ──
class Metrics:
    def __init__(self):
        self.llm_decision_calls = 0
        self.llm_resolve_calls = 0
        self.messages_sent = 0
        self.interactions_total = 0
        self.rule_actions = 0

metrics = Metrics()

async def run_agent(agent, world, brain, systems, agent_id, max_actions=3):
    agent_layer = agent.get("agent")
    actions_done = 0

    while actions_done < max_actions:
        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0:
            elapsed = 0

        systems["decay"].tick(agent, elapsed)
        systems["sensory"].update(agent, world.entities)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # Check busy result
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            print(f"  [{agent.name}] 📖 {result.narrative[:60]}...")

        # Check inbox
        inbox_msgs = agent_layer.inbox.drain()
        if inbox_msgs:
            for m in inbox_msgs:
                print(f"  [{agent.name}] 📬 收到 {m.from_agent_name}: \"{m.content[:30]}\"")

        # Decide if idle
        if agent.status == "idle":
            sensory = agent_layer.sensory
            memory = agent_layer.memory
            zone_data = world.get_zone_data(agent.zone)
            drives = agent_layer.drives

            # Filter interactable: exclude self, include other agents
            interactable_records = sensory.get_interactable()
            visible_records = sensory.get_visible_only()

            # Show agent what they perceive
            nearby_names = [r.name for r in interactable_records]
            print(f"  [{agent.name}] 📍 ({agent.pos[0]},{agent.pos[1]}) sees: {nearby_names}")

            # Build prompt context
            context = {
                "round": actions_done + 1,
                "name": agent.name,
                "personality": agent_layer.personality,
                "drives_table": drives.to_prompt_table(),
                "zone_name": zone_data.get("name", ""),
                "zone_width": zone_data.get("width", 0),
                "zone_height": zone_data.get("height", 0),
                "pos_x": agent.pos[0],
                "pos_y": agent.pos[1],
                "interactable_text": sensory.to_prompt_vision(),
                "visible_text": "",
                "memory_text": memory.to_prompt_text(3),
                "messages_text": "",
            }

            # Add inbox context if there are messages
            if inbox_msgs:
                msg_text = "\n".join(
                    f"- {m.from_agent_name}对你说: {m.content[:40]}"
                    for m in inbox_msgs
                )
                if inbox_msgs[0].method:
                    msg_text += f"\n(对方想和你{inbox_msgs[0].method})"
                context["messages_text"] = msg_text

            decision = await brain.decide(context)
            metrics.llm_decision_calls += 1

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
                            metrics.interactions_total += 1
                            if act_def.resolve.value == "rule":
                                metrics.rule_actions += 1
                            else:
                                metrics.llm_resolve_calls += 1
                            print(f"  [{agent.name}] 🎯 {action_name} {target.name}")

                    elif act_def.target_type.value == "agent":
                        # Agent-to-agent: send inbox message
                        world.send_message(agent.id, target_id, action_name,
                                           f"{agent.name}想和你{action_name}")
                        metrics.messages_sent += 1
                        actions_done += 1
                        print(f"  [{agent.name}] 💬 {action_name} → {target.name} (inbox)")

            # Reply to inbox messages
            reply_to = decision.get("respond_to")
            reply_text = decision.get("reply")
            if reply_to and reply_text:
                world.send_message(agent.id, reply_to, "reply", reply_text)
                print(f"  [{agent.name}] ↩ 回复 {world.entities.get(reply_to, {}).name if hasattr(world.entities.get(reply_to, object()), 'name') else reply_to}: {reply_text[:30]}")
                actions_done += 1

        # Sleep
        wait = 2.0 if agent.status == "busy" else 1.0
        await asyncio.sleep(wait)

    # Wait for final pending result
    for _ in range(20):
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)
            print(f"  [{agent.name}] 📖 (final) {result.narrative[:60]}...")
            break
        if agent.status == "idle":
            break
        await asyncio.sleep(1.0)


async def main():
    # Load configs
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
        "捡起": "硬币落地的叮当声",
    }
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(resolver, sound_map),
        "decay": DecaySystem(),
    }

    world = World(world_cfg, systems)

    # ── Register 2 additional agents ──
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

    print("=" * 60)
    print("  Phase A: 3-Agent Concurrent Test")
    print("=" * 60)
    for a in agents:
        inter = a.get("interaction")
        print(f"  {a.name:4s} at ({a.pos[0]},{a.pos[1]}) "
              f"thirst={inter.private_attrs.get('thirst',0):.0f} "
              f"coins={inter.private_attrs.get('coins',0)} "
              f"social={inter.private_attrs.get('social',0):.0f}")
    print()

    # Run all 3 concurrently
    tasks = [
        run_agent(agents[i], world, brain, systems, i, max_actions=3)
        for i in range(3)
    ]
    await asyncio.gather(*tasks)

    # ── Verification ──
    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)
    passed = 0
    failed = 0

    for a in agents:
        inter = a.get("interaction")
        pa = inter.private_attrs
        mem = a.get("agent").memory

        # Check attribute bounds
        for attr in ["thirst", "hunger", "social", "energy", "fun", "mood"]:
            v = pa.get(attr, 0)
            if 0 <= v <= 100:
                passed += 1
            else:
                failed += 1
                print(f"  ❌ {a.name}.{attr}={v} out of bounds!")

        # Check coins non-negative
        if pa.get("coins", 0) >= 0:
            passed += 1
        else:
            failed += 1
            print(f"  ❌ {a.name}.coins={pa['coins']} negative!")

        # Print final state
        print(f"  {a.name:4s} thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0)} "
              f"mood={pa.get('mood',0):.0f} social={pa.get('social',0):.0f} "
              f"mem={len(mem.entries)}")

    print(f"\n  Metrics:")
    print(f"    LLM decisions: {metrics.llm_decision_calls}")
    print(f"    LLM resolves:  {metrics.llm_resolve_calls}")
    print(f"    Rule actions:  {metrics.rule_actions}")
    print(f"    Messages:      {metrics.messages_sent}")
    print(f"    Total interactions: {metrics.interactions_total}")

    print(f"\n  Attributes: {passed} ok, {failed} violations")
    if failed:
        print("  ❌ PHASE A FAILED")
    else:
        print("  ✅ PHASE A PASSED")


if __name__ == "__main__":
    asyncio.run(main())
