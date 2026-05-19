<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v11-ff6b35?style=flat-square" alt="v11">
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

纯 Python 异步多智能体自主世界引擎。25 个 LLM 驱动 Agent 跨 3 个 Zone 自主社交、穿越、协作。支持**三世界观热切换**——猎魔人·老友记·蜘蛛侠——全部行为 YAML 配置驱动；Python 代码**零认知决策**。34 源文件，~1900 行 Python，~450 行 YAML 配置。

### 核心断言

> **引擎提供世界。LLM 提供认知。**
>
> 引擎报告事实：`mood=5`、gate 存在、target 实体可交互。
> 引擎不解释意图：不说"心情很差"、不说"应该穿越"、不说"这是目标"。
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

统一的数据写入入口。接受 `{"layer.property.sub_field": value}` 格式的 dotted-path 更新，引擎盲目执行，不解释语义。**v10 新增路径中间节点 None 检查**——遇不存在路径优雅跳过而非静默吞异常。`InteractionLayer.readonly` 提供硬性写约束。LLM #2 输出的 `target_changes` 经引擎 guard 后自动写回实体——NPC 可修改世界。

### 6. Director — 受控模式

freeze/snap/order/unfreeze/release。Agent 可在自主模式（KL→LLM）和受控模式（操作者→order）间动态切换。外部 Agent 通过 `SessionManager.join/leave` 进入世界，同 ID 恢复历史记忆。功能完整，loop 层已接入入口，生产激活待后续。

### 7. 多世界观热切换 — `--world` CLI

换世界观 = 换一个 YAML 文件。同一套 prompt/pipeline/loop 驱动任意世界观。已建三世界：

| 文件 | 世界观 | Zones | NPCs | Items |
|------|--------|-------|------|-------|
| `config/world.yaml` | 猎魔人·白果园 | 3 | 25 | 42 |
| `config/world_friends.yaml` | 老友记·Central Perk | 3 | 7 | 10 |
| `config/world_spiderman.yaml` | 蜘蛛侠·纽约市 | 3 | 6 | 8 |

属性名相同（`thirst hunger social energy fun mood coins`）→ prompts.yaml 不改一字。替换属性集仅需改 `prompts.yaml` 中的属性列表字符串。

### 8. 外部 Agent 接入 — Gateway API

任何外部 agent（人类或 LLM）通过 REST/WebSocket/MCP 接入运行中的世界。`WorldGateway` 管理权限和生命周期，`SessionManager` 处理 spawn/despawn/memory 持久化。零引擎代码改动。加入→感知→行动→离开 全部是同一套 `perceive()` / `act()` 协议——和自主 agent 共享同一决策通道。

---

## 实证结果

**180s 测试（25 Agent, 3 Zone, DeepSeek-chat, v11）：**

| 指标 | 数值 |
|------|------|
| 总行动 | **455** |
| NPC↔NPC 率 | **356 (78%)** |
| NPC→Item 率 | **99 (22%)** |
| `target_changes` 写入 | **9** |
| 属性校验 | ✅ 全通过 |
| Stuck loop (≥3×) | **0** |
| 认知代码 (Python) | **0 行** |

**1200s 测试（20min, 25 Agent, 3 Zone）：**

| 指标 | 数值 |
|------|------|
| 总行动 | **3,996** |
| NPC↔NPC 率 | **3,298 (83%)** |
| NPC→Item 率 | **698 (17%)** |
| Zone 活跃 | **3/3** |

**多世界 60min 验证（三世界各 20min）：**

| 世界 | NPCs | 行动 | NPC↔NPC% | 状态 |
|------|------|------|-----------|------|
| 猎魔人 | 25 | 3,996 | 83% | ✅ |
| 老友记 (修复后) | 7 | ~1,448† | 90%† | ✅ |
| 蜘蛛侠 (修复后) | 6 | ~1,392† | 76%† | ✅ |

†修复 NPC 分布后 10min 数据折算

### 功能验证

| 功能 | 状态 | 测试 |
|------|------|------|
| `update_entity()` dotted-path 盲赋值 | ✅ | v10 路径 None 检查 + target_changes 写入验证 |
| `InteractionLayer.readonly` 约束 | ✅ | 引擎 guard — 不向 LLM 暴露 |
| `target_changes` NPC 修改 item | ✅ | 9 次写入 / 180s（修复后实际生效） |
| `SessionManager` join/leave/memory | ✅ | 功能完整 (test)，生产入口待激活 |
| `Director` controlled 模式 | ✅ | 同上 — loop 已接入，缺实例化 |
| `despawn_entity()` | ✅ | entities dict + spatial grid 同步 |
| `--world` 多世界热切换 | ✅ | 三世界配置验证 + 60min 运行 |
| Error collector 结构化跟踪 | ✅ | v10 全面接入 — 替代 print(stderr) |
| Memory 相对时间戳 | ✅ | v10 修复 — 基准为显示窗口第一条 |

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
AgentWorld_Async/               # 34 files · ~2200 lines Python · ~450 lines YAML
├── config/
│   ├── world.yaml              # 猎魔人 — 25 NPC, 3 zones, 42 items
│   ├── world_friends.yaml      # 老友记 — 7 NPC, 3 zones, 10 items
│   ├── world_spiderman.yaml    # 蜘蛛侠 — 6 NPC, 3 zones, 8 items
│   └── world_test.yaml         # 评估测试 — 8 NPC, 2 zones
│   ├── prompts.yaml            # 15 slots, sensory_prompts, output schemas
│   └── llm.yaml                # provider (DeepSeek/OpenAI/MiniMax)
├── src/
│   ├── layers/                 # Visual, Auditory, Interaction, Agent, Base (5)
│   ├── entity/                 # Entity model (1)
│   ├── systems/                # Sensory, Interaction, Decay (3)
│   ├── agent/                  # Brain, Memory, Drives, SensoryMemory (4)
│   ├── core/                   # World, KL, Director, Session, Lifecycle, SpatialGrid, Clock (7)
│   ├── gateway/                # WorldGateway, REST/WS API, MCP tools (3)
│   ├── eval/                   # Metrics registry, report, 18 indicators (7)
│   ├── llm/                    # LLM client (1)
│   ├── prompt/                 # Assembler, Loader (2)
│   └── loop.py                 # 4-phase pipeline
├── main.py                     # CLI entry · --validate-config · --world · --eval-report · --api-port
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

# 多世界热切换
python main.py --world config/world_friends.yaml    # 老友记
python main.py --world config/world_spiderman.yaml  # 蜘蛛侠

# 评估
python main.py --eval-report trace.json      # 结构化评估报告

# 外部 Agent 接入
python main.py --api-port 8765              # 启动 Gateway API
# curl -X POST localhost:8765/sessions -d '{"agent_id":"...","agent_def":{...}}'
```

---

## 版本

| Ver | Milestone |
|-----|-----------|
| **v11** | Gateway API — 外部 Agent join/perceive/act/leave · `--api-port` · WorldGateway 权限管理 · MCP 工具定义 · `state_description` 自然语言状态注入 · 评估模块 (eval) — 18 个指标 · `--eval-report` · 死代码清理 (intent_ttl/STALE/interactions表/drive.currency) |
| **v10** | 多世界热切换 (`--world`) · 老友记+蜘蛛侠世界观 · philosophy cleanup: 删除 proximity+3 fallback · 删除 Intent STALE 标记 · `action_guidance` 通用化 · `update_entity` 路径 None 检查 · error_collector 全面接入 · `call_template` 统一 LLM 调用 · temperature 配置实际生效 · memory 时间戳修复 |
| **v9** | `update_entity()` dotted-path 盲赋值 · `target_changes` NPC 可修改 item · `readonly`/`filepath` 声明 · `Director` 受控模式 · `SessionManager` 外部 agent 生命周期 |
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

A pure-Python asynchronous multi-agent autonomous world engine. Up to 25 LLM-driven agents socialize, traverse zones, and collaborate across a persistent world. **Hot-swappable between three world configurations** — The Witcher · Friends · Spider-Man — fully YAML-configured; Python contains **zero cognitive decision-making code**. 34 source files, ~1900 lines Python, ~450 lines YAML.

### Core Thesis

> **The engine provides facts. The LLM provides cognition.**
>
> The engine reports `mood=5`. Not "you are depressed."
> The engine reports a gate exists. Not "you should cross zones."
> The engine reports a target is interactable. Not "this is your objective."
> All cognitive judgments emerge from the priority-ordered combination of **declarative YAML slots**.
>
> 📄 [DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md) · [META_PHILOSOPHY.md](META_PHILOSOPHY.md) · [PAPER.md](PAPER.md)

---

## Core Contributions

1. **Slot Vector Architecture.** Twelve YAML slots replace GA's ~730 lines of cognitive Python. A 45-line Assembler iterates an ordered template slot list, activates by `condition`, renders by `template`. New cognitive capability = one slot definition + one template reference. Zero Python changes.

2. **P/Q/KL Attention Gate.** The agent maintains internal world model P, compares to sensory input Q every 0.3s. P=Q → zero LLM calls. P≠Q → agent decides. Four-channel parallel diff.

3. **Per-Attribute Drive System.** Each attribute declares `{min, max, decay, description}` in YAML. Engine renders raw data only; the LLM interprets descriptions to decide urgency. Switch worlds = switch attribute lists. No engine labels, no hardcoded thresholds.

4. **Three-Channel Sensory.** Visual (look·detail) · Auditory (speech content) · Interaction (description·transit markers). All rendering templates defined in YAML `sensory_prompts`. Gate entities appear in the interaction channel marked for traversal.

5. **Runtime Entity Mutability.** `update_entity()` accepts `{"layer.property.sub_field": value}` dotted-path updates, executed blindly — zero semantic interpretation. **v10 adds intermediate path None-checking** — gracefully skips non-existent paths rather than silently failing. `InteractionLayer.readonly` provides a declarative write constraint, never exposed to the LLM. LLM #2 `target_changes` are applied through an engine guard — NPCs modify the world.

6. **Director Controlled Mode.** freeze/snap/order/unfreeze/release. Agents switch between autonomous (KL→LLM) and controlled (operator→order) modes. `SessionManager` enables external agent lifecycle with memory persistence. Production entry fully wired via `--api-port`.

7. **Multi-World Hot-Swap.** Switch worlds by switching one YAML file. Same prompt pipeline, same loop, same assembler. Three shipped worlds.

8. **External Agent Gateway.** Any external agent (human or LLM) joins a running world via REST/WebSocket/MCP. `WorldGateway` manages permissions and lifecycle. `join→perceive→act→leave` uses the same decision channel as autonomous agents — zero special treatment.

| File | World | Zones | NPCs | Items |
|------|-------|-------|------|-------|
| `world.yaml` | The Witcher · White Orchard | 3 | 25 | 42 |
| `world_friends.yaml` | Friends · Central Perk | 3 | 7 | 10 |
| `world_spiderman.yaml` | Spider-Man · NYC | 3 | 6 | 8 |

Shared attribute names (`thirst hunger social energy fun mood coins`) → zero prompt changes. Substitute the attribute set by editing one string in `prompts.yaml`.

---

## Empirical Results

**180s run (25 agents, 3 zones, DeepSeek-chat, v11):**

| Metric | Value |
|--------|-------|
| Total actions | **455** |
| NPC↔NPC rate | **356 (78%)** |
| NPC→Item rate | **99 (22%)** |
| `target_changes` applied | **9** |
| Attribute validation | ✅ all passed |
| Stuck loops (≥3×) | **0** |
| Cognitive code | **0 lines** |

**1200s run (20min, 25 agents, 3 zones):**

| Metric | Value |
|--------|-------|
| Total actions | **3,996** |
| NPC↔NPC rate | **3,298 (83%)** |
| NPC→Item rate | **698 (17%)** |
| Zones active | **3/3** |

**Multi-world 60min validation (3 worlds × 20min):**

| World | NPCs | Actions | NPC↔NPC% | Result |
|-------|------|---------|-----------|--------|
| Witcher | 25 | 3,996 | 83% | ✅ |
| Friends (fixed) | 7 | ~1,448† | 90%† | ✅ |
| Spider-Man (fixed) | 6 | ~1,392† | 76%† | ✅ |

†Projected from 10min post-fix data

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
