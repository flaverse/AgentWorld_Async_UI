"""Geralt full trace with timestamps and structured report."""
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
REPORT_FILE = os.path.join(BASE, "geralt_report.md")


class GeraltReport:
    def __init__(self):
        self.entries = []
        self.start_time = time.time()

    def ts(self):
        return f"{time.time() - self.start_time:.1f}s"

    def add(self, section, content):
        self.entries.append({
            "time": self.ts(),
            "section": section,
            "content": content,
        })

    def write(self):
        lines = [
            f"# 杰洛特 (Geralt) — 完整决策追踪报告",
            f"",
            f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**人物**: 利维亚的杰洛特，狼学派猎魔人",
            f"**性格**: 寡言少语，行事果断。刚完成水鬼委托，回白果园休整",
            f"**初始**: thirst=60 hunger=50 coins=150 social=20 energy=85 fun=15 mood=50",
            f"",
            f"---",
            f"",
        ]
        for e in self.entries:
            lines.append(f"## {e['section']}  (⏱ +{e['time']})")
            lines.append("")
            lines.append(e["content"])
            lines.append("")
        with open(REPORT_FILE, "w") as f:
            f.write("\n".join(lines))
        return REPORT_FILE


report = GeraltReport()


async def trace_geralt():
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
    agent = world.entities["geralt"]
    agent_layer = agent.get("agent")
    pa = agent.get("interaction").private_attrs

    # ── Init report ──
    report.add("🟢 初始化",
        f"**zone**: {world.zones[agent.zone]['name']}  |  **pos**: ({agent.pos[0]},{agent.pos[1]})\n\n"
        f"| 属性 | 初始值 |\n|------|--------|\n"
        f"| thirst | {pa['thirst']:.0f} |\n| hunger | {pa['hunger']:.0f} |\n"
        f"| coins | {pa['coins']} |\n| social | {pa['social']:.0f} |\n"
        f"| energy | {pa['energy']:.0f} |\n| fun | {pa['fun']:.0f} |\n"
        f"| mood | {pa['mood']:.0f} |\n"
    )

    for action_num in range(6):
        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0: elapsed = 0
        systems["decay"].tick(agent, elapsed)
        systems["sensory"].update(agent, world.entities)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # ── Layer 1: Busy Result ──
        if agent.busy_result is not None:
            r = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(r, agent, world)

            extra = ""
            if r.move_to_zone:
                extra = f"\n\n**🚪 传送**: zone → `{r.move_to_zone}`, pos → `{r.move_to_pos}`"

            report.add(f"📖 交互结果: {agent.name}",
                f"**narrative**: {r.narrative}\n\n"
                f"**caller_deltas**: `{json.dumps(r.caller_deltas, ensure_ascii=False)}`\n\n"
                f"**ambient_effects**: `{json.dumps(r.ambient_effects, ensure_ascii=False)}`{extra}"
            )

        if agent.status != "idle":
            await asyncio.sleep(2.0)
            continue

        sensory = agent_layer.sensory
        drives = agent_layer.drives
        memory = agent_layer.memory
        zone_data = world.get_zone_data(agent.zone)
        pa = agent.get("interaction").private_attrs

        # ── Layer 2: Sensory Input ──
        interactable = sensory.get_interactable()
        visible = sensory.get_visible_only()

        sense_md = f"**zone**: {world.zones[agent.zone]['name']}  |  **pos**: ({agent.pos[0]},{agent.pos[1]})\n\n"

        # Drive state
        sense_md += "### 欲望状态\n\n"
        sense_md += "| 属性 | 值 | 紧迫度 |\n|------|-----|--------|\n"
        for k, v in drives.attrs.items():
            if k == "coins":
                continue
            if v >= 80: u = "⚠️ 急需"
            elif v >= 60: u = "● 关注"
            else: u = "○ 正常"
            sense_md += f"| {k} | {v:.0f}/100 | {u} |\n"
        sense_md += f"| coins | {pa.get('coins',0)} | — |\n"

        # Interactable entities
        sense_md += "\n### ✅ 可直接交互\n\n"
        if interactable:
            for r in interactable:
                sense_md += f"- **{r.name}** (`{r.entity_id}`) pos=({r.pos[0]},{r.pos[1]}) | {r.visual_data.get('look','')}\n"
                if r.actions:
                    sense_md += f"  - actions: {r.actions}\n"
                if "detail" in r.visual_data:
                    sense_md += f"  - detail: {r.visual_data['detail']}\n"
        else:
            sense_md += "(无 — 需要移动才能找到可交互实体)\n"

        # Visible entities
        sense_md += "\n### 👁️ 可见但够不着\n\n"
        if visible:
            for r in visible:
                sense_md += f"- **{r.name}** (`{r.entity_id}`) pos=({r.pos[0]},{r.pos[1]}) dist={r.distance} | {r.visual_data.get('look','')}\n"
        else:
            sense_md += "(无)\n"

        # Memory
        mem_entries = memory.recent(5)
        if mem_entries:
            sense_md += "\n### 🧠 最近记忆\n\n"
            for m in mem_entries:
                sense_md += f"- {m.get('narrative','?')}\n"

        report.add(f"👁️ 感知输入 #{action_num+1}", sense_md)

        # ── Layer 3: LLM Decision ──
        visible_text = ""
        if visible:
            visible_text = "\n".join(
                f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | dist={r.distance}"
                for r in visible
            )
        context = {
            "round": action_num + 1, "name": agent.name,
            "personality": agent_layer.personality,
            "drives_table": drives.to_prompt_table(),
            "zone_name": zone_data.get("name", agent.zone),
            "zone_width": zone_data.get("width", 10),
            "zone_height": zone_data.get("height", 10),
            "pos_x": agent.pos[0], "pos_y": agent.pos[1],
            "interactable_text": sensory.to_prompt_vision(),
            "visible_text": visible_text,
            "memory_text": memory.to_prompt_text(5),
            "messages_text": "", "hearing_text": sensory.to_prompt_hearing(),
        }

        t0 = time.time()
        decision = await brain.decide(context)
        llm_time = time.time() - t0

        decision_md = f"**LLM 耗时**: {llm_time:.1f}s\n\n"
        decision_md += f"**thinking**: {decision.get('thinking', '—')}\n\n"
        decision_md += f"**move_to**: `{decision.get('move_to')}`\n\n"
        decision_md += f"**target_entity**: `{decision.get('target_entity')}`\n\n"
        decision_md += f"**action**: `{decision.get('action')}`\n"

        report.add(f"🧠 LLM 决策 #{action_num+1} ({llm_time:.1f}s)", decision_md)

        # ── Layer 4: Execution ──
        exec_steps = []

        move_to = decision.get("move_to")
        if move_to and isinstance(move_to, list) and len(move_to) == 2:
            dist = agent.move_to(move_to)
            agent.last_action_time = world.clock.now()
            exec_steps.append(f"🚶 移动: ({agent.pos[0]},{agent.pos[1]}) → ({move_to[0]},{move_to[1]})，耗时 {dist} 分钟")
            systems["sensory"].update(agent, world.entities)
            systems["interaction"].update_sensory(agent, world.entities)

        target_id = decision.get("target_entity")
        action_name = decision.get("action")
        if target_id and action_name and target_id in world.entities:
            target = world.entities[target_id]
            il = target.get("interaction")
            if il and il.get_action(action_name):
                ad = il.get_action(action_name)
                exec_steps.append(f"🎯 交互: `{action_name}` → **{target.name}** (`{target_id}`)")
                exec_steps.append(f"   - target_type: `{ad.target_type.value}`")
                exec_steps.append(f"   - resolve: `{ad.resolve.value}`")

                if ad.target_type.value == "passive":
                    if systems["interaction"].can_interact(agent, target):
                        if ad.resolve.value == "llm":
                            amb = world.get_ambient_entities(target, radius=2, exclude={agent.id})
                            if amb:
                                exec_steps.append("   - 📋 LLM #2 裁判视野:")
                                for a in amb:
                                    exec_steps.append(f"     - {a['name']} dist={a['distance']} | {json.dumps(a['private_hint'], ensure_ascii=False)}")
                        iid = uuid.uuid4().hex[:8]
                        systems["interaction"].submit(iid, agent, target, action_name, world)
                        agent.last_action_time = world.clock.now()
                        exec_steps.append("   - → 已提交后台裁定, agent busy")
                    else:
                        exec_steps.append("   - ❌ 不在交互范围")
                elif ad.target_type.value == "agent":
                    world.send_message(agent.id, target_id, action_name, f"{agent.name}想和你{action_name}")
                    exec_steps.append("   - → 已发送 inbox 消息")

        if not exec_steps:
            exec_steps.append("(无操作)")

        report.add(f"🔧 执行 #{action_num+1}", "\n".join(exec_steps))

        await asyncio.sleep(2.5)

    # ── Final state ──
    pa = agent.get("interaction").private_attrs
    final_md = "| 属性 | 初始 | 最终 | 变化 |\n|------|------|------|------|\n"
    initials = {"thirst": 60, "hunger": 50, "coins": 150, "social": 20, "energy": 85, "fun": 15, "mood": 50}
    for k, init_v in initials.items():
        final_v = pa.get(k, 0)
        delta = final_v - init_v
        sign = "+" if delta > 0 else ""
        final_md += f"| {k} | {init_v:.0f} | {final_v:.0f} | {sign}{delta:.0f} |\n"

    final_md += "\n### 记忆记录\n\n"
    for e in agent_layer.memory.entries:
        final_md += f"- {e.get('narrative', '?')}\n"

    report.add("🏁 最终状态", final_md)

    path = report.write()
    print(f"Report written to: {path}")
    print(open(path).read())


if __name__ == "__main__":
    asyncio.run(trace_geralt())
