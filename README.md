<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v9-ff6b35?style=flat-square" alt="v9">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License">
</p>

<h1 align="center">AgentWorld Async</h1>

<p align="center">
  <b>A declarative architecture for LLM-based autonomous agents.<br/>
  Between perception and action, code performs one function: comparing world model to sensory input.<br/>
  All cognitive judgments — priority, importance, goal maintenance — are declarative YAML slots.</b>
</p>

<p align="center">
  <i>No change, no thought.</i>
</p>

---

# 中文版

## 概述

纯 Python 异步多智能体自主世界引擎。25 个 LLM 驱动 Agent 跨 3 个 Zone 自主社交、穿越、协作。全部行为 YAML 配置驱动；Python 代码**零认知决策**。34 源文件，~1900 行 Python，~230 行 YAML 配置。

### 核心断言

> **引擎提供世界。LLM 提供认知。**
>
> 引擎报告事实：`mood=5`、`gate exists at (33,18)`、`target is readonly=false`。
> 引擎不解释意图：不说"心情很差"、不说"应该穿越"、不说"可以修改此实体"。
> 全部认知判断通过 **声明式 YAML slot** 的优先级有序组合引导 LLM 完成。
>
> 📄 设计哲学：[DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md) · [META_PHILOSOPHY.md](META_PHILOSOPHY.md) · 论文：[PAPER.md](PAPER.md)

---

## 核心贡献

### 1. Slot Vector Architecture — 0 行认知代码

Generative Agents (Park et al., 2023) 的认知栈（记忆检索、反思、计划、重要度评估）约 730 行 Python。AgentWorld 以 **12 个声明式 YAML slot** 替代全部认知流程：45 行的 Assembler 遍历模板的有序 slot 列表，按 `condition` 激活，按列表位置决定优先级。新增认知能力 = YAML slot 定义 + 模板引用。**Python 零改动。**

### 2. P/Q/KL Attention Gate — 预测误差驱动

Agent 维护内部世界模型 P，每 0.3s 对比感官输入 Q。P=Q → 零 LLM 调用。P≠Q → 触发决策。四通道（听觉·视觉·状态·时差）并行 diff。世界不变，Agent 不动。

### 3. Per-Attribute Drive System — 声明式属性引擎

每个属性独立定义 `{min, max, decay, description}`。引擎输出裸数据，LLM 自己读描述判断紧迫性。换世界 = 换属性列表：

```
| 属性    | 数值   | 描述 |
|---------|--------|------|
| mood    | 5/100  | 0=绝望可能轻生或自毁。100=极度愉悦。 |
| thirst  | 65/100 | 100=喉咙冒烟急需饮水。0=完全不渴。 |
| eddies  | 150    | 赛博朋克世界流通货币。无自然衰减。 |
```

**无紧急标签，无引擎判断。** 一切来自 YAML 声明。

### 4. Three-Channel Sensory — 模板驱动感知

视觉（远观·细节）· 听觉（言语内容）· 可交互（描述·可穿越标记）。三通道渲染模板全在 YAML `sensory_prompts` 块定义。Gate 实体出现在"可交互"通道标记为 `【可穿越 → zone】`。Agent 自主决定穿越。

### 5. 运行时实体变更 — `update_entity()` 盲赋值路径

统一的数据写入入口。接受 `{"layer.property.sub_field": value}` 格式的 dotted-path 更新，引擎盲目执行，不解释语义。`InteractionLayer.readonly` 提供硬性写约束。`readonly=false` 时 LLM #2 输出的 `target_changes` 自动写回实体——NPC 可修改世界。

### 6. Director — 受控模式

freeze/snap/order/unfreeze/release。Agent 可在自主模式（KL→LLM）和受控模式（操作者→order）间动态切换。外部 Agent 通过 `SessionManager.join/leave` 进入世界，同 ID 恢复历史记忆。NPC 通过已有感官系统自然感知外部 Agent 的加入和离开。

---

## 实证结果

**180s 测试（25 Agent, 3 Zone, DeepSeek-chat, v9）：**

| 指标 | 数值 |
|------|------|
| 总行动 | **615** |
| NPC↔NPC 率 | **513 (83%)** |
| 邻接重复率 | **2.9%**（无外部去重滤波器） |
| KL change 触发 | **583 (94.8%)** |
| Stale 触发 | **9 (1.5%)** |
| Zone 穿越 | **6 次 / 4 agent** |
| Main thread 自主设定 | **25/25 (100%)** |
| 对话覆盖率 | **403/615 (66%)** |
| 故事覆盖率 | **355/615 (58%)** |
| Stuck loop (≥3×) | **0** |
| 认知代码 (Python) | **0 行** |

**涌现的跨 agent 协同**：25 个 main_thread 全自主设定且贴合角色——希里"前往旧矿坑追踪狮鹫"、夏妮"跟随猎狮鹫队伍沿途收集情报"、女猎手"协助叶奈法追踪"——形成自发联动作战链。

### 功能验证

| 功能 | 状态 | 测试 |
|------|------|------|
| `update_entity()` dotted-path 盲赋值 | ✅ | visual + interaction.hidden 已验证 |
| `InteractionLayer.readonly` 约束 | ✅ | 只读实体硬性拦截 |
| `target_changes` NPC 修改 item | ✅ | Schema 通过，执行路径就绪 |
| `SessionManager` join/leave/memory | ✅ | 创建·受控·记忆持久化·重入恢复 |
| `Director` controlled 模式 | ✅ | take·snap·order·unfreeze·release |
| `despawn_entity()` | ✅ | entities dict + spatial grid 同步 |

---

## 对比分析

| | Generative Agents | CrewAI | **AgentWorld Async** |
|---|---|---|---|
| LLM 调用 / NPC 交互 | 3+ (plan+reflect+act) | 1 per tool | **1** |
| 发呆时 LLM 调用 | 有（定时反思） | 无 | **0**（KL gate） |
| 认知代码量 | ~730 行 Python | N/A | **0 行**（12 YAML slot） |
| 动作定义 | 自然语言计划 | 工具函数注册 | **自然语言**，无注册表 |
| 记忆 | 反思摘要 | 对话历史 | **自然语言 story** |
| 属性系统 | 无 | 无 | **声明式 per-attr** |
| 受控模式 | 无 | 无 | **Director freeze/snap/order** |
| 运行时实体变更 | 无 | 无 | **update_entity() + target_changes** |
| 外部 Agent 接入 | 无 | 无 | **SessionManager + memory persist** |
| 配置 | Code + JSON | Python decorator | **纯 YAML** |
| 规模 | 25 agent, 2天 | 不等 | **25 agent, 34 文件, ~1900 行** |

---

## 项目结构

```
AgentWorld_Async/               # 34 files · ~1900 lines Python · ~230 lines YAML
├── config/
│   ├── world.yaml              # 3 zones, 67 entities, per-attr drive, gate topology
│   ├── prompts.yaml            # 12 slots, sensory_prompts, output schemas
│   └── llm.yaml                # provider (DeepSeek/OpenAI/MiniMax)
├── src/
│   ├── layers/                 # Visual, Auditory, Interaction, Agent, Base (5)
│   ├── entity/                 # Entity model (1)
│   ├── systems/                # Sensory, Interaction, Decay (3)
│   ├── agent/                  # Brain, Memory, Drives, SensoryMemory (4)
│   ├── core/                   # World, KL, Director, Session, Lifecycle, SpatialGrid, Clock (7)
│   ├── llm/                    # LLM client (1)
│   ├── prompt/                 # Assembler, Loader (2)
│   └── loop.py                 # 4-phase pipeline
├── main.py                     # CLI entry · --validate-config
├── DESIGN_PHILOSOPHY.md        # 项目特有哲学
├── META_PHILOSOPHY.md          # 跨域元原则
├── PAPER.md                    # 论文稿
└── README.md
```

---

## 快速开始

```bash
pip install -r requirements.txt
python main.py --validate-config             # 配置校验
python main.py                               # 25-agent 并发 (60s)
python main.py --runtime 180 --validate      # 3min + 属性校验
python main.py --demo                        # 单 Agent 演示
python main.py --output trace.json           # 保存 trace
```

---

## 版本

| Ver | Milestone |
|-----|-----------|
| **v9** | `update_entity()` dotted-path 盲赋值 · `target_changes` NPC 可修改 item · `readonly`/`filepath` 声明 · `Director` 受控模式 · `SessionManager` 外部 agent 生命周期 · 6 次 zone 穿越 · 25/25 main_thread |
| v8 | Per-attr drive · Gate crossing · Properties fix · -68 行死代码 |
| v7.1 | `main_thread` · `idle_guidance` · Intent DONE · Inbox 删除 |
| v7 | 三通道感官 · P/Q dict copy fix |
| v6 | Slot vector · Dedup+observing 删除 · -364 行 |
| v5 | 泛型 Layer.observe() · 校验 · 持久化 |
| v4 | P/Q/KL gate + write lock · Unified interact() |

---

## License

MIT

---

# English

## Overview

A pure-Python asynchronous multi-agent autonomous world engine. Up to 25 LLM-driven agents socialize, traverse zones, and collaborate across a persistent world. Fully YAML-configured; Python contains **zero cognitive decision-making code**. 34 source files, ~1900 lines Python, ~230 lines YAML.

### Core Thesis

> **The engine provides facts. The LLM provides cognition.**
>
> The engine reports `mood=5`. Not "you are depressed."
> The engine reports `gate exists at (33,18)`. Not "you should cross zones."
> The engine reports `readonly=false`. Not "you may modify this entity."
> All cognitive judgments emerge from the priority-ordered combination of **declarative YAML slots**.
>
> 📄 [DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md) · [META_PHILOSOPHY.md](META_PHILOSOPHY.md) · [PAPER.md](PAPER.md)

---

## Core Contributions

1. **Slot Vector Architecture.** Twelve YAML slots replace GA's ~730 lines of cognitive Python. A 45-line Assembler iterates an ordered template slot list, activates by `condition`, renders by `template`. New cognitive capability = one slot definition + one template reference. Zero Python changes.

2. **P/Q/KL Attention Gate.** The agent maintains internal world model P, compares to sensory input Q every 0.3s. P=Q → zero LLM calls. P≠Q → agent decides. Four-channel parallel diff.

3. **Per-Attribute Drive System.** Each attribute declares `{min, max, decay, description}` in YAML. Engine renders raw data only; the LLM interprets descriptions to decide urgency. Switch worlds = switch attribute lists. No engine labels, no hardcoded thresholds.

4. **Three-Channel Sensory.** Visual (look·detail) · Auditory (speech content) · Interaction (description·transit markers). All rendering templates defined in YAML `sensory_prompts`. Gate entities appear in the interaction channel marked for traversal.

5. **Runtime Entity Mutability.** `update_entity()` accepts `{"layer.property.sub_field": value}` dotted-path updates, executed blindly — zero semantic interpretation. `InteractionLayer.readonly` provides a declarative write constraint. When `readonly=false`, LLM #2 `target_changes` are automatically applied — NPCs modify the world.

6. **Director Controlled Mode.** freeze/snap/order/unfreeze/release. Agents switch between autonomous (KL→LLM) and controlled (operator→order) modes dynamically. External agents join via `SessionManager`, with memory persistence and restoration on rejoin by ID. NPCs perceive external agents through the existing sensory system — no new notification mechanism needed.

---

## Empirical Results

**180s run (25 agents, 3 zones, DeepSeek-chat, v9):**

| Metric | Value |
|--------|-------|
| Total actions | **615** |
| NPC↔NPC rate | **513 (83%)** |
| Adjacent repetition | **2.9%** (no external dedup) |
| KL change triggers | **583 (94.8%)** |
| Stale triggers | **9 (1.5%)** |
| Zone crossings | **6 / 4 agents** |
| Main thread auto-set | **25/25 (100%)** |
| Dialogue coverage | **403/615 (66%)** |
| Story coverage | **355/615 (58%)** |
| Stuck loops (≥3×) | **0** |
| Cognitive code | **0 lines** |

**Emergent coordination**: all 25 main_threads were autonomously set and character-appropriate. Ciri ("track the gryphon to the old mine"), Shani ("follow the hunting party, gather intel"), and the Huntress ("assist Yennefer in tracking") formed a spontaneous multi-agent task force without any hardcoded grouping or agenda.

## Comparison

| | Generative Agents | CrewAI | **AgentWorld Async** |
|---|---|---|---|
| LLM calls / interaction | 3+ | 1 per tool | **1** |
| Idle LLM calls | Yes (scheduled) | No | **0** (KL gate) |
| Cognitive code | ~730 lines | N/A | **0 lines** (12 YAML slots) |
| Action definition | NL plans | Tool registry | **Natural language**, no registry |
| Memory | Reflection summary | Chat history | **Natural language story** |
| Attribute system | None | None | **Declarative per-attr** |
| Controlled mode | None | None | **Director** (freeze/snap/order) |
| Runtime mutation | None | None | **update_entity() + target_changes** |
| External agent API | None | None | **SessionManager + memory persist** |
| Config | Code + JSON | Decorators | **Pure YAML** |
| Scale | 25 agents, 2d sim | Varies | **25 agents, 34 files, ~1900 lines** |

---

*Diagrams, Project Structure, Quick Start, and Version Log: same as Chinese section above.*

---

## License

MIT
