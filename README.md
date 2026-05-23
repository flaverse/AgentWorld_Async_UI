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

纯 Python 异步多智能体自主世界引擎。25 个 LLM 驱动 Agent 跨 3 个 Zone 自主社交、穿越、协作。支持**三世界观热切换**——猎魔人·老友记·蜘蛛侠——全部行为 YAML 配置驱动；Python 代码**零认知决策**。~40 源文件，~2200 行 Python，~450 行 YAML 配置。

### 核心断言

> **引擎提供事实。LLM 提供认知。**
>
> 引擎报告：`mood=5`、gate 存在、`target_name` 精确匹配成功。
> 引擎不判断：不说"心情很差"、不说"应该穿越"、不说"你可能想找的是这个实体"。
> 全部认知判断通过 **声明式 YAML slot** 的优先级有序组合引导 LLM 完成。
>
> 📄 设计哲学：[DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md) · 论文：[PAPER.md](PAPER.md)

---

## 核心贡献

### 1. Slot Vector Architecture — 45 行声明式调度引擎（零行领域特定的认知代码）

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

统一的数据写入入口。接受 `{"layer.property.sub_field": value}` 格式的 dotted-path 更新，引擎盲目执行，不解释语义。路径中间节点 None 检查——遇不存在路径优雅跳过而非静默吞异常。`InteractionLayer.readonly` 提供硬性写约束。LLM #2 输出的 `target_changes` 经引擎 guard 后自动写回实体——NPC 可修改世界。

### 6. 精确目标解析 — LLM 输出 `target_name`

引擎删除全部模糊匹配启发式代码（substring、word-match、proximity fallback），替换为精确名称匹配。LLM #1 输出 `target_name` 字段，从感官实体列表中精确抄写目标名。引擎只做存在性检查。实证验证：100% target_name 采纳率，零失败交互，NPC↔NPC 率从 56% 跃升至 90%。

### 7. Director — 受控模式

freeze/snap/order/unfreeze/release。Agent 可在自主模式（KL→LLM）和受控模式（操作者→order）间动态切换。被控 agent 在 Phase 0 即跳过所有计算周期——零感官/KL 浪费。外部 Agent 通过 `SessionManager.join/leave` 进入世界，同 ID 恢复历史记忆。

### 8. 多世界观热切换 — `--world` CLI

换世界观 = 换一个 YAML 文件。同一套 prompt/pipeline/loop 驱动任意世界观。已建三世界：

| 文件 | 世界观 | Zones | NPCs | Items |
|------|--------|-------|------|-------|
| `config/world.yaml` | 猎魔人·白果园 | 3 | 25 | 42 |
| `config/world_friends.yaml` | 老友记·Central Perk | 3 | 7 | 10 |
| `config/world_spiderman.yaml` | 蜘蛛侠·纽约市 | 3 | 6 | 8 |

属性名相同（`thirst hunger social energy fun mood coins`）→ prompts.yaml 不改一字。替换属性集仅需改 `prompts.yaml` 中的属性列表字符串。

### 9. 外部 Agent 接入 — Gateway API

任何外部 agent（人类或 LLM）通过 REST/WebSocket/MCP 接入运行中的世界。`WorldGateway` 管理权限和生命周期，`SessionManager` 处理 spawn/despawn/memory 持久化。零引擎代码改动。加入→感知→行动→离开 全部是同一套 `perceive()` / `act()` 协议——和自主 agent 共享同一决策通道。

---

## 实证结果

**P0 修复验证（8 NPC, 2 Zone, 180s, v11）：**

| 指标 | 修复前 | 修复后 | 变化 |
|------|--------|--------|------|
| `target_name` 采纳率 | — | **100%** (158/158) | 首个 cycle 即完全适应 |
| INTENT/DONE 内存残留 | — | **0** | 引擎零篡改 agent 记忆 |
| 失败交互 | — | **0** | 精确名称匹配无歧义 |
| NPC↔NPC 率 | 56% | **90%** | +34 pp |
| 对话覆盖率 | 64% | **86%** | +22 pp |
| 对话链数 | 5-7 | **19** | +170% |
| 邻接重复率 | 1.9% | **0.7%** | 引擎不强制重试 |
| KL 闲置周期 | 被控 agent 浪费 | **0** (Phase 0 跳过) | |

**1200s 测试（20min, 25 Agent, 3 Zone）：**

| 指标 | 数值 |
|------|------|
| 总行动 | **3,996** |
| NPC↔NPC 率 | **3,298 (83%)** |
| NPC→Item 率 | **698 (17%)** |
| Zone 活跃 | **3/3** |
| Stuck loop (≥3×) | **0** |

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
| `update_entity()` dotted-path 盲赋值 | ✅ | 路径 None 检查 + target_changes 写入验证 |
| `InteractionLayer.readonly` 约束 | ✅ | 引擎 guard — 不向 LLM 暴露 |
| `target_changes` NPC 修改 item | ✅ | 写入验证通过 |
| `target_name` 精确匹配 | ✅ | 100% 采纳率，零模糊匹配 |
| INTENT 机制完全删除 | ✅ | 零 memory 残留，零引擎调度器 |
| `speech_window` YAML 化 | ✅ | 移至 sensory_prompts.auditory.window_seconds |
| `SessionManager` join/leave/memory | ✅ | 功能完整，生产入口已激活 |
| `Director` controlled 模式 | ✅ | Phase 0 跳过，零资源浪费 |
| `--world` 多世界热切换 | ✅ | 四世界配置验证 + 60min 运行 |
| `--eval-report` 评估系统 | ✅ | 18 指标，5 类别，零引擎依赖 |
| `--api-port` Gateway API | ✅ | join→perceive→act→leave 闭环 |

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
| 外部 Agent 接入 | 无 | 无 | **Gateway API + MCP** |
| 评估系统 | 无 | 无 | **18 指标，5 类别** |
| 目标解析 | LLM 模糊匹配 | 工具注册 | **LLM 输出 target_name** |
| 配置 | Code + JSON | Python decorator | **纯 YAML** |
| 规模 | 25 agent, 2天 | 不等 | **25 agent, ~40 文件, ~2200 行** |

---

## 项目结构

```
AgentWorld_Async/               # ~40 files · ~2200 lines Python · ~450 lines YAML
├── config/
│   ├── world.yaml              # The Witcher — 25 NPC, 3 zones
│   ├── world_friends.yaml      # Friends — 7 NPC, 3 zones
│   ├── world_spiderman.yaml    # Spider-Man — 6 NPC, 3 zones
│   └── world_test.yaml         # Evaluation benchmark — 8 NPC, 2 zones
│   ├── prompts.yaml            # 15 slots, sensory_prompts, output schemas
│   └── llm.yaml                # provider (DeepSeek/OpenAI/MiniMax)
├── src/
│   ├── layers/                 # Visual, Auditory, Interaction, Agent, Base
│   ├── entity/                 # Entity model
│   ├── systems/                # Sensory, Interaction, Decay
│   ├── agent/                  # Brain, Memory, Drives, SensoryMemory
│   ├── core/                   # World, KL Gate, Director, Session, Lifecycle, SpatialGrid
│   ├── gateway/                # WorldGateway, REST/WS API, MCP tools
│   ├── eval/                   # 18 metrics, registry, report
│   ├── llm/                    # LLM client
│   ├── prompt/                 # Assembler, Loader
│   └── loop.py                 # 3-phase pipeline (sense → KL gate → decide → act)
├── main.py                     # CLI: --world --eval-report --api-port
├── DESIGN_PHILOSOPHY.md
├── PAPER.md
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
| **v12** | 三层 slot 组 (contract/world/npc) · slot_groups 二维矩阵 · per-agent traits 系统 · intent_context 战术反馈 · drive 分拆 values+context · prompt token 减 2/3 · Phoenix 去"必须" · PEP 8 兼容 |
| **v11** | 哲学自检 (P0): `target_name` 匹配 · `speech_window` YAML 化 · Director Phase 0 · Gateway API · 评估 18 指标 · 4 世界配置 |
| **v10** | 多世界热切换 · 哲学清理: proximity fallback 删除 · error_collector · temperature 生效 |
| **v9** | `update_entity()` 盲赋值 · `target_changes` · Director · SessionManager |
| v8 | Per-attr drive · Gate crossing · Properties fix · -68 行死代码 |
| v7.1 | `main_thread` · Inbox 删除 |
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

A pure-Python asynchronous multi-agent autonomous world engine. Up to 25 LLM-driven agents socialize, traverse zones, and collaborate across a persistent world. **Hot-swappable between three world configurations** — The Witcher · Friends · Spider-Man — fully YAML-configured; Python contains **YAML-defined decision logic**. 34 source files, ~1900 lines Python, ~450 lines YAML.

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

3. **Per-Attribute Drive System.** Each attribute declares `{min, max, decay, description}` in YAML. Engine renders raw data only; the LLM interprets descriptions to decide urgency. Switch worlds = switch attribute lists.

4. **Three-Channel Sensory.** Visual · Auditory · Interaction. All rendering templates defined in YAML `sensory_prompts`. Sensory parameters (`window_seconds`, header formats) fully YAML-configured — zero hardcoded engine values.

5. **Runtime Entity Mutability.** `update_entity()` dotted-path updates, blindly executed. `InteractionLayer.readonly` provides declarative write constraint. LLM #2 `target_changes` applied through engine guard.

6. **Exact Target Resolution.** Engine performs zero heuristic matching. LLM #1 outputs `target_name` — engine does exact name lookup. Verified: 100% adoption, zero failed interactions, NPC↔NPC rate 56%→90%.

7. **Director Controlled Mode.** freeze/snap/order/unfreeze/release. Controlled agents skip all compute cycles at Phase 0 — zero sensory/KL waste. `SessionManager` handles external agent lifecycle with memory persistence.

8. **Multi-World Hot-Swap.** Switch worlds by switching one YAML file. Four shipped worlds.

| File | World | Zones | NPCs | Items |
|------|-------|-------|------|-------|
| `world.yaml` | The Witcher · White Orchard | 3 | 25 | 42 |
| `world_friends.yaml` | Friends · Central Perk | 3 | 7 | 10 |
| `world_spiderman.yaml` | Spider-Man · NYC | 3 | 6 | 8 |

Shared attribute names (`thirst hunger social energy fun mood coins`) → zero prompt changes. Substitute the attribute set by editing one string in `prompts.yaml`.

---

## Empirical Results

**P0 fix validation (8 NPC, 2 zones, 180s, v11):**

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| `target_name` adoption | — | **100%** (158/158) | First cycle |
| INTENT/DONE residuals | — | **0** | Clean |
| Failed interactions | — | **0** | Exact name match |
| NPC↔NPC rate | 56% | **90%** | +34 pp |
| Dialogue coverage | 64% | **86%** | +22 pp |
| Conversation chains | 5–7 | **19** | +170% |
| Adjacent repetition | 1.9% | **0.7%** | No forced retry |

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
