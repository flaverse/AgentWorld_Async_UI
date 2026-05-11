"""Geralt raw prompt-level trace — every LLM prompt in full."""
import sys, os, yaml, asyncio, uuid, json, time
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
OUT = os.path.join(BASE, "geralt_prompts.md")


async def main():
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
        "interaction": InteractionSystem(resolver, {"饮用": "杯子碰吧台声"}),
        "decay": DecaySystem(),
    }
    world = World(world_cfg, systems)
    agent = world.entities["geralt"]
    agent_layer = agent.get("agent")
    pa = agent.get("interaction").private_attrs

    t0 = time.time()
    ts = lambda: f"{time.time()-t0:.1f}s"

    output = []
    output.append("# 杰洛特 — 完整 Prompt 级追踪")
    output.append(f"\n生成: {time.strftime('%H:%M:%S')}")
    output.append(f"\n初始: thirst={pa['thirst']:.0f} hunger={pa['hunger']:.0f} coins={pa['coins']} social={pa['social']:.0f} energy={pa['energy']:.0f} fun={pa['fun']:.0f}")
    output.append(f"\n---\n")

    for rnd in range(6):
        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0: elapsed = 0
        systems["decay"].tick(agent, elapsed)
        systems["sensory"].update(agent, world.entities, world)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # Busy result
        if agent.busy_result is not None:
            r = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(r, agent, world)
            output.append(f"### 📖 LLM #2 裁定结果 (⏱ {ts()})\n")
            output.append(f"narrative: {r.narrative}\n")
            output.append(f"caller_deltas: {json.dumps(r.caller_deltas, ensure_ascii=False)}\n")
            output.append(f"ambient_effects: {json.dumps(r.ambient_effects, ensure_ascii=False)}\n")
            if r.move_to_zone:
                output.append(f"🚪 zone → {r.move_to_zone} pos → {r.move_to_pos}\n")
            output.append("\n---\n")

        if agent.status != "idle":
            await asyncio.sleep(2.0)
            continue

        sensory = agent_layer.sensory
        drives = agent_layer.drives
        memory = agent_layer.memory
        zone_data = world.get_zone_data(agent.zone)
        pa = agent.get("interaction").private_attrs

        output.append(f"## 第 {rnd+1} 次决策 — {world.zones[agent.zone]['name']} ({agent.pos[0]},{agent.pos[1]}) (⏱ {ts()})\n")

        # ── RAW PROMPT for LLM #1 ──
        visible_text = ""
        if sensory.get_visible_only():
            visible_text = "\n".join(
                f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | dist={r.distance}"
                for r in sensory.get_visible_only()
            )
        context = {
            "round": rnd + 1,
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
            "memory_text": memory.to_prompt_text(5),
            "messages_text": "",
            "hearing_text": sensory.to_prompt_hearing(),
        }
        prompt = assembler.assemble("agent_decision", context)

        output.append("### 📥 LLM #1 原始输入 (Prompt)\n")
        output.append("```")
        output.append(prompt)
        output.append("```\n")

        # LLM call
        t_llm = time.time()
        decision = await brain.decide(context)
        llm_time = time.time() - t_llm

        output.append(f"### 📤 LLM #1 原始输出 (⏱ {llm_time:.1f}s)\n")
        output.append("```json")
        output.append(json.dumps(decision, ensure_ascii=False, indent=2))
        output.append("```\n")

        # Execute
        move_to = decision.get("move_to")
        if move_to and isinstance(move_to, list) and len(move_to) == 2:
            dist = agent.move_to(move_to)
            agent.last_action_time = world.clock.now()
            output.append(f"🚶 移动 → ({move_to[0]},{move_to[1]}) 耗时 {dist}min\n")
            systems["sensory"].update(agent, world.entities, world)
            systems["interaction"].update_sensory(agent, world.entities)

        target_id = decision.get("target_entity")
        action_name = decision.get("action")
        if target_id and action_name and target_id in world.entities:
            target = world.entities[target_id]
            il = target.get("interaction")
            if il and il.get_action(action_name):
                ad = il.get_action(action_name)

                if ad.target_type.value == "passive" and ad.resolve.value == "llm":
                    # ── RAW PROMPT for LLM #2 ──
                    ambient = world.get_ambient_entities(target, radius=2, exclude={agent.id})

                    resolver_ctx = {
                        "caller_name": agent.name,
                        "caller_public": json.dumps(
                            agent.get("interaction").public_attrs, ensure_ascii=False
                        ),
                        "caller_private": json.dumps(
                            agent.get("interaction").private_attrs, ensure_ascii=False
                        ),
                        "target_name": target.name,
                        "target_public": json.dumps(
                            il.public_attrs, ensure_ascii=False
                        ),
                        "target_private": json.dumps(
                            il.private_attrs, ensure_ascii=False
                        ),
                        "action": action_name,
                        "ambient_text": resolver._format_ambient(ambient),
                    }
                    resolver_prompt = assembler.assemble("interaction_resolve", resolver_ctx)

                    output.append(f"### 📥 LLM #2 原始输入 (裁判 Prompt)\n")
                    output.append("```")
                    output.append(resolver_prompt)
                    output.append("```\n")

                if systems["interaction"].can_interact(agent, target):
                    iid = uuid.uuid4().hex[:8]
                    systems["interaction"].submit(iid, agent, target, action_name, world)
                    agent.last_action_time = world.clock.now()
                    output.append(f"🎯 {action_name} → {target.name} (busy, 等待 LLM #2...)\n")
                else:
                    output.append(f"❌ {target.name} 不在交互范围\n")

                output.append("\n---\n")

        await asyncio.sleep(2.5)

    output.append(f"\n---\n生成时间: {time.strftime('%H:%M:%S')}")
    with open(OUT, "w") as f:
        f.write("\n".join(output))
    print(f"Report: {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
