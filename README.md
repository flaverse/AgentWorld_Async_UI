<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v12-ff6b35?style=flat-square" alt="v12">
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

纯 Python 异步多智能体自主世界引擎。LLM 驱动 Agent 跨 Zone 自主社交、穿越、协作。支持**三世界观热切换**——猎魔人·老友记·蜘蛛侠——全部行为 YAML 配置驱动。45 行 Assembler 是纯字符串格式化引擎，零领域语义。**14 个 slot 分 3 层** (contract/world/npc)，`slot_groups.yaml` 二维矩阵控制 slot 激活，per-agent traits 系统声明行为倾向。~50 源文件，~2400 行 Python，~600 行 YAML 配置。

### 核心断言

> **引擎提供事实。LLM 提供认知。**
>
> 引擎报告：`mood=5`、gate 存在、`target_name` 精确匹配成功。
> 引擎不判断：不说"心情很差"、不说"应该穿越"、不说"你可能想找的是这个实体"。
> 全部认知判断通过 **声明式 YAML slot** 的优先级有序组合引导 LLM 完成。
>
> 📄 设计哲学：[DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md)

---

## 核心贡献

### 1. Slot Vector Architecture — 14 Slot, 3 层, 45 行声明式调度引擎

Generative Agents (Park et al., 2023) 的认知栈（记忆检索、反思、计划、重要度评估）约 730 行 Python。AgentWorld 以 **14 个声明式 YAML slot 分 3 层** 替代全部认知流程。45 行 Assembler 遍历模板的有序 slot 列表，按 `condition` 激活，按 `slot_groups.yaml` 二维矩阵控制 per-agent slot 开关。新增认知能力 = YAML slot 定义 + 模板引用。**Python 零改动。**

三层模型：
- **Contract 层** — `action_scope`, `output_contract`（输出契约，永开）
- **World 层** — `spatial_context`, `sensory_section`, `gate_highlight`, `delta_gate`（环境信息，世界级共享）
- **NPC 层** — `persona`, `main_thread`, `drive_values`, `drive_context`, `recent_memory`, `conversation_context`, `behavioral_traits`, `intent_context`（per-agent 可配置）

### 2. Per-Agent Traits — 声明式行为倾向

行为倾向（persistent、novelty-seeking、conversational_patience、socially_reciprocal、satisficing、goal_directed）是独立的 YAML 模板，通过 `traits` 矩阵 per-agent 分配。`behavioral_traits` slot 只在 traits 非空时渲染。Phoebe 零 trait → 纯 persona 驱动。Gunther `[persistent, goal_directed]` → 接收坚持偏置。消融实验 = 改一行 YAML。

### 3. Intent Context — 战术反馈，零判断

引擎追踪上轮 LLM 意图 (`intent`)、意图重复次数 (`intent_streak`)、对话不对称性 (`my_messages` vs `their_messages`)。`intent_context` slot 只报告事实——不判断"成功/失败"。Ross 看到"第 8 轮追 Rachel"后由自己的 `persistent` trait 决定继续还是收手。

### 4. P/Q Delta Gate — 预测误差驱动

Agent 维护内部世界模型 P，每 ~0.3s 对比感官输入 Q。P=Q → 零 LLM 调用。P≠Q → 触发决策。四通道（听觉·视觉·状态·时差）并行 diff。世界不变，Agent 不动。prompt token 节省 2/3。

每个属性独立定义 `{min, max, decay, description}`。引擎输出裸数据，LLM 自己读描述判断紧迫性。换世界 = 换属性列表：

```
| 属性    | 数值   | 描述 |
|---------|--------|------|
| mood    | 5/100  | 0=绝望可能轻生或自毁。100=极度愉悦。 |
| thirst  | 65/100 | 100=喉咙冒烟急需饮水。0=完全不渴。 |
| eddies  | 150    | 赛博朋克世界流通货币。无自然衰减。 |
```

**无紧急标签，无引擎判断。** 一切来自 YAML 声明。

### 5. Per-Attribute Drive System — 声明式属性引擎

视觉（远观·细节）· 听觉（言语内容）· 可交互（描述·可穿越标记）。三通道渲染模板全在 YAML `sensory_prompts` 块定义。Gate 实体出现在"可交互"通道标记为 `【可穿越 → zone】`。Agent 自主决定穿越。

### 6. Three-Channel Sensory — 模板驱动感知

统一的数据写入入口。接受 `{"layer.property.sub_field": value}` 格式的 dotted-path 更新，引擎盲目执行，不解释语义。路径中间节点 None 检查——遇不存在路径优雅跳过而非静默吞异常。`InteractionLayer.readonly` 提供硬性写约束。LLM #2 输出的 `target_changes` 经引擎 guard 后自动写回实体——NPC 可修改世界。

### 7. 运行时实体变更 — `update_entity()` 盲赋值路径

引擎删除全部模糊匹配启发式代码（substring、word-match、proximity fallback），替换为精确名称匹配。LLM #1 输出 `target_name` 字段，从感官实体列表中精确抄写目标名。引擎只做存在性检查。实证验证：100% target_name 采纳率，零失败交互，NPC↔NPC 率从 56% 跃升至 90%。

### 8. 精确目标解析 — LLM 输出 `target_name`

freeze/snap/order/unfreeze/release。Agent 可在自主模式（KL→LLM）和受控模式（操作者→order）间动态切换。被控 agent 在 Phase 0 即跳过所有计算周期——零感官/KL 浪费。外部 Agent 通过 `SessionManager.join/leave` 进入世界，同 ID 恢复历史记忆。

### 9. Director — 受控模式

换世界观 = 换一个 YAML 文件。同一套 prompt/pipeline/loop 驱动任意世界观。已建三世界：

| 文件 | 世界观 | Zones | NPCs | Items |
|------|--------|-------|------|-------|
| `config/world.yaml` | 猎魔人·白果园 | 3 | 25 | 42 |
| `config/world_friends.yaml` | 老友记·Central Perk | 3 | 7 | 10 |
| `config/world_spiderman.yaml` | 蜘蛛侠·纽约市 | 3 | 6 | 8 |

属性名相同（`thirst hunger social energy fun mood coins`）→ prompts.yaml 不改一字。替换属性集仅需改 `prompts.yaml` 中的属性列表字符串。

### 10. 多世界观热切换 — `--world` CLI

### 11. 外部 Agent 接入 — Gateway API

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
| 认知代码量 | ~730 行 Python | N/A | **0 行**（14 YAML slot） |
| 动作定义 | 自然语言计划 | 工具函数注册 | **自然语言**，无注册表 |
| 记忆 | 反思摘要 | 对话历史 | **自然语言 story** |
| 属性系统 | 无 | 无 | **声明式 per-attr** |
| 受控模式 | 无 | 无 | **Director freeze/snap/order** |
| 运行时实体变更 | 无 | 无 | **update_entity() + target_changes** |
| 外部 Agent 接入 | 无 | 无 | **Gateway REST/WebSocket** |
| 评估系统 | 无 | 无 | **18 指标，5 类别** |
| 目标解析 | LLM 模糊匹配 | 工具注册 | **LLM 输出 target_name** |
| 配置 | Code + JSON | Python decorator | **纯 YAML** |
| 规模 | 25 agent, 2天 | 不等 | **25 agent, ~50 文件, ~2400 行** |

---

## 项目结构

```
AgentWorld_Async/               # ~50 files · ~2400 lines Python · ~600 lines YAML
├── config/
│   ├── world.yaml              # 猎魔人 — 25 NPC, 3 zones
│   ├── world_friends.yaml      # 老友记 — 7 NPC, 3 zones
│   ├── world_spiderman.yaml    # 蜘蛛侠 — 6 NPC, 3 zones
│   ├── prompts.yaml            # 14 slots, traits, sensory_prompts, schemas
│   ├── slot_groups.yaml        # 三层矩阵: contract/world/npc, 多 group
│   ├── llm.yaml                # multi-provider (DeepSeek/MiniMax)
│   └── _sim_defaults.yaml      # 共享模拟默认值
├── src/
│   ├── cli/                    # CLI 模块 (config, commands, runner, report)
│   ├── layers/                 # Visual, Auditory, Interaction, Agent, Base
│   ├── entity/                 # Entity model
│   ├── systems/                # Sensory, Interaction, Decay
│   ├── agent/                  # Brain, Memory, Drives, SensoryMemory
│   ├── core/                   # World, Delta Gate, Director, Session, Lifecycle
│   ├── gateway/                # WorldGateway, REST/WS API
│   ├── eval/                   # 18 metrics, registry, report
│   ├── llm/                    # LLM client + ConcurrencyGate
│   ├── prompt/                 # Assembler, Loader
│   ├── telemetry/              # TelemetryCollector (API latency tracking)
│   └── loop.py                 # 4-phase pipeline (freeze→sense→gate→decide→act)
├── main.py                     # CLI: --world --eval-report --api-port --demo
├── DESIGN_PHILOSOPHY.md
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

A pure-Python asynchronous multi-agent autonomous world engine. LLM-driven agents socialize, traverse zones, and collaborate. **Hot-swappable between three world configurations** — The Witcher · Friends · Spider-Man — fully YAML-configured. 45-line Assembler is a pure string formatter with zero domain semantics. **14 slots in 3 layers** (contract/world/npc), `slot_groups.yaml` matrix controls slot activation, per-agent traits system declares behavioral tendencies. ~50 files, ~2400 lines Python, ~600 lines YAML.

### Core Thesis

> **The engine provides facts. The LLM provides cognition.**
>
> The engine reports `mood=5`. Not "you are depressed."
> The engine reports a gate exists. Not "you should cross zones."
> All cognitive judgments emerge from the combination of **declarative YAML slots**.
>
> 📄 [DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md)

---

## Core Contributions

1. **Slot Vector Architecture (14 slots, 3 layers).** 14 YAML slots in 3 independent layers replace GA's ~730 lines of cognitive Python. A 45-line Assembler iterates an ordered template slot list, activates by `condition`, filters by `slot_groups.yaml` matrix. Contract layer (always-on output rules), World layer (environment facts shared per world), NPC layer (per-agent configurable via `npc-group`).

2. **Per-Agent Traits System.** Behavioral tendencies (persistent, novelty-seeking, conversational_patience, etc.) are declarative YAML templates assigned per-agent via a `traits` matrix. The `behavioral_traits` slot renders only when traits are assigned. Phoebe with zero traits operates purely on persona; Gunther with `[persistent, goal_directed]` receives persistence bias.

3. **Intent Context — Tactical Feedback.** Engine tracks prior intent, intent repetition count, and conversation asymmetry (`my_messages` vs `their_messages`). The `intent_context` slot reports only facts—no "success/failure" judgment. Ross sees "attempt 8 of inviting Rachel" and decides via his `persistent` trait whether to continue or pivot.

4. **P/Q Delta Gate.** The agent maintains internal world model P, compares to sensory input Q. P=Q → zero LLM calls. P≠Q → agent decides. Four-channel parallel diff. Prompt tokens reduced by 2/3.

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
| Cognitive code | ~730 lines | N/A | **0 lines** (14 YAML slots) |
| Action definition | NL plans | Tool registry | **Natural language**, no registry |
| Memory | Reflection summary | Chat history | **Natural language story** |
| Attribute system | None | None | **Declarative per-attr** |
| Controlled mode | None | None | **Director** (freeze/snap/order) |
| Runtime mutation | None | None | **update_entity() + target_changes** |
| External agent API | None | None | **Gateway REST/WebSocket** |
| Slot group matrix | None | None | **slot_groups.yaml** (per-agent configurable) |
| Config | Code + JSON | Decorators | **Pure YAML** |
| Scale | 25 agents, 2d sim | Varies | **50 files, ~2400 lines** |

---

*Diagrams, Project Structure, Quick Start, and Version Log: same as Chinese section above.*

---

## License

MIT
