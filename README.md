<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20MiniMax-green?style=flat-square">
  <img src="https://img.shields.io/badge/architecture-v12-ff6b35?style=flat-square">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square">
</p>

<h1 align="center">AgentWorld Async</h1>

<p align="center">
  <b>引擎提供事实。LLM 提供认知。<br/>世界不变，Agent 不动。</b>
</p>

---

<p align="center">
  <img src="img/architecture.png?v=2" alt="Architecture" width="100%">
</p>

---

# 中文版

## 五个核心思想

### 1. 引擎报告，LLM 判断

引擎不教 agent 怎么做。引擎只报告事实：`mood=5`、gate 存在、`target_name` 匹配成功。不说"心情很差"、不说"应该穿越"。全部认知判断权在 LLM，通过 YAML slot 组合引导。

### 2. 声明式认知架构 — 14 Slot，3 层

Generative Agents 的 730 行认知代码 → 14 个 YAML slot + 45 行字符串格式化引擎。三层：
- **Contract** — 输出契约 (`action_scope` / `output_contract`)
- **World** — 环境事实 (`delta_gate` / `spatial` / `sensory` / `gate_highlight`)
- **NPC** — 角色驱动 (`persona` / `main_thread` / `drive_values` / `drive_context` / `memory` / `conversation` / `traits` / `intent_context`)

`slot_groups.yaml` 二维矩阵控制 per-agent slot 激活。新认知 = 加一行 YAML。零 Python 改动。

### 3. P/Q Delta Gate — 世界不变，Agent 不动

Agent 维护内部世界模型 P，每帧对比感官 Q。P=Q → 零 LLM 调用。P≠Q → 触发决策。四通道并行 diff。发呆不花钱。Token 节省 2/3。

### 4. Per-Agent Traits + 战术意图反馈

行为倾向是声明式 trait 模板——`persistent`（坚持）、`novelty_seeking`（喜新）、`conversational_patience`（对话耐心）等——通过 YAML 矩阵 per-agent 分配。引擎追踪上轮意图、重复次数、对话不对称性，只报告事实。Ross 看到"第 8 轮追 Rachel"，由自己的 `persistent` trait 决定继续还是收手。消融实验 = 改一行 YAML。

### 5. 世界观即配置

换世界 = 换 YAML 文件。同一引擎驱动猎魔人酒馆、老友记咖啡厅、蜘蛛侠纽约。属性名相同 → prompts.yaml 一字不改。Gateway REST/WebSocket 接口——外部 agent 通过 `join/perceive/act` 与自主 agent 共享同一决策通道。

---

## vs. Generative Agents

<p align="center">
  <img src="img/slot_vs_ga.png?v=2" alt="SVA vs GA" width="100%">
</p>

---

## 实证 (v12, 7 Agents, 180s, Friends)

| 指标 | 数值 |
|------|------|
| 总行动 | **206** |
| 对话率 | **99%** (204/206) |
| 线程完成率 | **53%** (16/30) |
| 区域跨越 | **14 次** (6 agents) |
| NPC↔NPC 率 | **89%** |
| 心情改善 | **7/7** (+17.7) |
| 零空转 | 0% null actions |

---

## 快速开始

```bash
pip install -r requirements.txt
python main.py --validate-config
python main.py --demo --world config/world_friends.yaml
python main.py --runtime 180 --validate
python main.py --output trace.json
python main.py --eval-report trace.json
python main.py --api-port 8765
python main.py --world config/world_spiderman.yaml
```

---

## 版本

| Ver | 里程碑 |
|-----|--------|
| **v12** | 三层 slot 组 · slot_groups 矩阵 · per-agent traits · intent_context · token -67% |
| **v11** | target_name 精确匹配 · Director Phase 0 · Gateway API · 18 指标 |
| **v10** | 多世界热切换 · error_collector |
| **v9** | update_entity() · target_changes · SessionManager |
| **v8** | Per-attr drive · Gate crossing |
| **v7** | 三通道感官 · P/Q dict copy fix |
| **v6** | Slot vector · -364 行死代码 |
| **v5** | Layer.observe() · 校验 |
| **v4** | P/Q delta gate + write lock |

---

# English

## Five Principles

### 1. Engine Reports Facts, LLM Decides

The engine prescribes nothing. It reports `mood=5`, gate exists, `target_name` matched. Not "you are depressed," not "you should cross zones." All cognition emerges from LLM judgment, guided by YAML slot composition.

### 2. Declarative Cognitive Architecture — 14 Slots, 3 Layers

Generative Agents' 730 lines of cognitive Python → 14 YAML slots + 45-line string formatter. Three layers:
- **Contract** — output rules (`action_scope` / `output_contract`)
- **World** — environmental facts (`delta_gate` / `spatial` / `sensory` / `gate_highlight`)
- **NPC** — agent drivers (`persona` / `main_thread` / `drive_values` / `drive_context` / `memory` / `conversation` / `traits` / `intent_context`)

`slot_groups.yaml` matrix controls per-agent slot activation. New cognition = one YAML line. Zero Python changes.

### 3. P/Q Delta Gate — No Change, No Thought

Agent maintains internal world model P, compares to sensory input Q each tick. P=Q → zero LLM calls. P≠Q → agent decides. Four-channel parallel diff. Idle is free. Tokens reduced 67%.

### 4. Per-Agent Traits + Tactical Intent Feedback

Behavioral tendencies are declarative trait templates — `persistent`, `novelty_seeking`, `conversational_patience` — assigned per-agent via YAML matrix. Engine tracks prior intent, repetition count, conversation asymmetry. Reports facts only. Ross sees "attempt 8 inviting Rachel" and decides via his `persistent` trait. Ablation = one YAML line change.

### 5. Worlds Are Config Files

Swap worlds by swapping YAML files. Same engine drives The Witcher tavern, Friends coffee shop, Spider-Man NYC. Shared attribute names → zero prompt changes. Gateway REST/WebSocket API — external agents use same `join/perceive/act` protocol as autonomous agents.

---

## Quick Start

```bash
pip install -r requirements.txt
python main.py --validate-config
python main.py --demo --world config/world_friends.yaml
python main.py --runtime 180 --validate
python main.py --output trace.json
python main.py --eval-report trace.json
python main.py --api-port 8765
```

---

## License

MIT
