import yaml
import asyncio
import uuid
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "src"))

from core.world import World
from core.clock import WorldClock
from agent.brain import Brain
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from interaction.resolver import InteractionResolver
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem


async def main():
    # Load configs
    with open(os.path.join(base_dir, "config/world.yaml")) as f:
        world_cfg = yaml.safe_load(f)
    with open(os.path.join(base_dir, "config/llm.yaml")) as f:
        llm_cfg = yaml.safe_load(f)

    # Init
    loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
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
    agents = [e for e in world.entities.values()
              if e.get("agent") and e.get("agent").autonomous]

    if not agents:
        print("No autonomous agents found!")
        return

    agent = agents[0]
    agent_layer = agent.get("agent")

    print(f"Found agent: {agent.name}")
    print(f"  Personality: {agent_layer.personality}")
    print()
    print("=" * 60)
    print("  异步 Multi-Agent 自主世界 — Demo")
    print("=" * 60)

    # ─── 真正的异步主循环 ───
    action_count = 0
    while action_count < 5:
        agent_layer = agent.get("agent")
        drives = agent_layer.drives

        # 上次动作到现在过了多久
        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0:
            elapsed = 0

        # ① Decay
        systems["decay"].tick(agent, elapsed)

        # ② Sense
        systems["sensory"].update(agent, world.entities)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # ③ 检查 busy 结果
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None

            agent.apply_deltas(result.caller_deltas)
            if result.target_id and result.target_id in world.entities:
                world.entities[result.target_id].apply_deltas(result.target_deltas)
            for amb_eff in result.ambient_effects:
                aid = amb_eff.get("entity_id", "")
                if aid in world.entities:
                    world.entities[aid].apply_deltas(amb_eff.get("deltas", {}))

            agent_layer.memory.record(narrative=result.narrative)
            agent.status = "idle"

            print(f"\n⏱  {world.clock.time_str()} | {agent.name} ({agent.pos[0]},{agent.pos[1]})")
            print(f"  📖 {result.narrative}")
            if result.caller_deltas:
                print(f"     → 状态变化: {result.caller_deltas}")
            if result.ambient_effects:
                print(f"     → 周边影响: {result.ambient_effects}")

        # ④ Busy 时也能收消息 (demo 无多 agent，暂略)

        # ⑤ 空闲时决策
        if agent.status == "idle":
            zone_data = world.get_zone_data(agent.zone)
            sensory = agent_layer.sensory
            memory = agent_layer.memory

            context = {
                "round": action_count + 1,
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
                "memory_text": memory.to_prompt_text(5),
                "messages_text": "",
            }

            print(f"\n⏱  {world.clock.time_str()} | {agent.name} ({agent.pos[0]},{agent.pos[1]})")
            inter = agent.get("interaction")
            if inter:
                pa = inter.private_attrs
                print(f"  💭 想下一步... (thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0)})")

            decision = await brain.decide(context)

            # ⑥ Move
            move_to = decision.get("move_to")
            if move_to and isinstance(move_to, list) and len(move_to) == 2:
                move_time = agent.move_to(move_to)
                agent.last_action_time = world.clock.now()
                print(f"  🚶 移动到 ({move_to[0]},{move_to[1]})，耗时 {move_time} 分钟")
                systems["sensory"].update(agent, world.entities)
                systems["interaction"].update_sensory(agent, world.entities)

            # ⑦ Interact
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
                            action_count += 1
                            print(f"  🎯 {action_name} {target.name} → 后台裁定中...")
                        else:
                            print(f"  ⚠️  {target.name} 不在交互范围")

        # ⑧ 按 action 耗时 sleep（不是固定间隔）
        ad = agent.get("interaction")
        act_def = None
        if hasattr(agent, '_last_act_def'):
            act_def = agent._last_act_def

        if agent.status == "busy":
            remaining = agent.busy_until - world.clock.now()
            wait = max(0.5, min(remaining / world.time_scale, 3.0))
        else:
            wait = max(0.5, min(((agent.last_action_time or world.clock.now()) + 2 - world.clock.now()) / world.time_scale, 2.0))

        await asyncio.sleep(wait)

    # ─── 等待最后的结果 ───
    print("\n等待最后的裁定结果...")
    for _ in range(15):
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            agent.apply_deltas(result.caller_deltas)
            if result.target_id and result.target_id in world.entities:
                world.entities[result.target_id].apply_deltas(result.target_deltas)
            for amb_eff in result.ambient_effects:
                aid = amb_eff.get("entity_id", "")
                if aid in world.entities:
                    world.entities[aid].apply_deltas(amb_eff.get("deltas", {}))
            agent_layer.memory.record(narrative=result.narrative)
            agent.status = "idle"
            print(f"  📖 {result.narrative}")
            if result.caller_deltas:
                print(f"     → 状态变化: {result.caller_deltas}")
            break
        if agent.status == "idle":
            break
        await asyncio.sleep(1.0)

    # ─── 最终快照 ───
    inter = agent.get("interaction")
    print(f"\n{'=' * 60}")
    print(f"  最终状态 | {world.clock.time_str()} | {agent.name}")
    print("=" * 60)
    if inter:
        pa = inter.private_attrs
        print(f"  thirst={pa.get('thirst',0):.0f}  hunger={pa.get('hunger',0):.0f}  coins={pa.get('coins',0)}  energy={pa.get('energy',0):.0f}  fun={pa.get('fun',0):.0f}  mood={pa.get('mood',0):.0f}")
    print()
    print("记忆:")
    for entry in agent_layer.memory.entries:
        print(f"  {entry.get('narrative', '?')}")


if __name__ == "__main__":
    asyncio.run(main())
