<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/async-asyncio-purple" alt="Async">
  <img src="https://img.shields.io/badge/LLM-MiniMax%20%7C%20DeepSeek-green" alt="LLM">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="License">
</p>

<h1 align="center">
  🏠 AgentWorld Async
</h1>

<p align="center">
  <b>An Asynchronous, Layer-Architected, LLM-Driven Multi-Agent Autonomous World Engine</b><br/>
  <b>异步 · 分层架构 · LLM 驱动的多智能体自主世界引擎</b>
</p>

<p align="center">
  <i>"Every entity is a node. Every relationship is a position. Every decision is autonomous."</i><br/>
  <i>"位置即关系，决策即自由。"</i>
</p>

---

## 📖 Overview · 概述

**AgentWorld Async** is a ground-up reimagining of multi-agent simulation. Unlike traditional turn-based systems where agents march in lockstep to a global clock, each agent here runs as an independent `asyncio.Task` — deciding its own actions, moving at its own pace, and interacting through config-driven layer interfaces. The world is defined entirely in YAML. Zero behavior is hardcoded in Python.

**AgentWorld Async** 是对多智能体仿真的一次彻底重构。告别回合制全局时钟——每个 Agent 独立运行在 `asyncio.Task` 中，自己决定做什么、走多快、和谁交互。所有行为全部由 YAML 配置驱动，Python 代码零硬编码。

### 🆚 Comparison with v1 · 与 v1 对比

| Dimension · 维度 | AgentWorld v1 | AgentWorld Async (v2) |
|---|---|---|
| **Time Model · 时间** | Global tick clock: all agents act in lockstep. Daytime 30min/tick, night 6h/tick. Deterministic 50-tick batch runs. · 全局刻度同步 | Per-agent async: each agent acts at its own pace. Sleep = action duration. No central clock forcing simultaneous action. · 各自节奏 |
| **Entity Model · 实体** | Graph-first: entities are nodes in a weighted multi-digraph. NPC/zone/item/recipe each have subclass-like config (type_id, switches). Relationships = edges with quantity (qty=-1 = infinite). · 图节点 | Layer-container: single `Entity` class holds `layers: {visual, interaction, agent, ...}`. Relationships = spatial proximity (same coordinate = implies adjacency). No graph edges. · 层容器 |
| **Relationship · 关系** | Explicit directed edges: `npc→zone`, `npc→item(qty)`, `zone↔zone(bidirectional)`. Edge types have semantics (npc_zone, npc_item, npc_npc). `supply_view()` recursively aggregates inventory. · 显式边 | Implicit via co-location: entities at same [x,y] coexist independently. No container/parent fields. Position IS relationship. · 位置即关系 |
| **Interaction Model · 交互** | LLM outputs structured graph operations: `{"op":"delta","src":"npc_A","tgt":"item_coin","delta":-5}`. One unified `apply_edge_operations()` write path. Recipe transforms: consumes X → produces Y. · LLM 输出图操作 | LLM outputs narrative decisions: `{"target_entity":"drink_ale","action":"饮用"}`. `InteractionSystem` dispatches: resolve=rule (engine) or resolve=llm (LLM #2 judge with ambient entities). · LLM 叙事决策 |
| **Verification · 校验** | 8-check registry with mask-based activation. `entity_existence`, `capacity_upper_bound`, `degree_conservation` (Σ=0 per group), `json_format`, `quantity_accuracy`, etc. ConservationValidator with group-based pass/fail. Feedback loop for retry. · 8项校验注册表 | LLM #2 as implicit validator: sees private attrs of both parties + ambient entities. No formal verification registry (yet). Attribute clamping exists. · LLM #2 隐式校验 |
| **Config · 配置** | Two JSON files: `node_config.json` (ontology + entity defs) + `domain.json` (prompt slots, recipes, masks). ConfigAdapter provides type_id queries (has_role, is_terminal, prefix_to_type_id). · JSON 双文件 | Pure YAML: `world.yaml` (zones + tilemaps + entities with layer blocks) + `prompts.yaml` (system_prompts + templates + slots + output_schemas). Python zero hardcoded text. · 纯 YAML |
| **Prompt System · Prompt** | Slot-based assembly via `DomainAdapter`: provider=content → adapter.render_slot() via dynamic dispatch; provider=topology → engine-fixed renderers; provider=runtime → clock/feedback. Optional LLM translation layer converts abstract topology → NL. · Slot 组装 + 翻译层 | Same slot-based assembly: provider=content|runtime|topology. Simpler: no translation layer, no domain adapter subclass. Templates + slots + schemas all in YAML. PromptAssembler.format() directly. · 同 Slot 机制，更轻量 |
| **Persistence · 持久化** | Full SQLite: unified `nodes` table (id, type, name, data JSON). Self-seeding from config. Upsert pattern with created_at preservation. `sync_graph_to_nodes()` writes all entities back each tick. · SQLite 统一表 | Not yet implemented (demo runs in-memory). · 未实现 |
| **Spatial · 空间** | Zone-level: NPCs belong to a zone. Interaction determined by zone membership + graph edges. Movement = system_delta edge op (zone↔zone). · Zone 级 | Tile grid (x,y): continuous movement within zones. Interaction radius = min(agent_r, target_r). Gate entities for zone transitions. · 瓦片网格 |
| **Scale · 规模** | Production: 13 NPCs, 7 zones, 11 items, 6 recipes. 50-tick batch runs via subprocess isolation with timeout+retry. Comprehensive REPORT.md per tick. · 生产级 | Demo: 1 NPC, 1 zone, 5 entities. 5-interaction loop. Console output only. · Demo 级 |
| **Frontend · 前端** | Script output: `run_1tick.py` generates REPORT.md with timing tables, NPC state diffs, story highlights. No interactive UI. · 脚本报告 | Planned: Phaser.js 2D pixel-art renderer (Stardew Valley style). Tilemap layers + sprite animations + speech bubbles + WS real-time push. Backend sends JSON, frontend renders blindly. · 计划中 |
| **Agent Autonomy · Agent 自治** | Code-executed: `_decay_and_sync()` applies fixed passive decay (vitality-3, satiety-5 per tick). LLM plans constrained by label_mapping + topology_constraints. · 代码控制的被动衰减 | Drive-driven: each agent has `drives` dict with per-attribute decay rates. LLM freely decides based on drives + sensory + memory. Agent-to-agent via inbox (no external adjudication). · 欲望驱动自主决策 |
| **Code Style · 代码风格** | Heavy: 9 service files, domain adapter (~1460 lines), graph engine (~1163 lines). Strong typing via Pydantic models (NPC, NPCStatus, Position). Thread-safe contextvars for parallel tracing. · 重型工程化 | Light: single Entity class, Layer classes (~30 lines each), Systems (~50 lines each). No Pydantic models. Dataclass-based. · 轻量敏捷 |
| **Key Innovation · 核心创新** | Topology-content decoupling: engine kernel operates on abstract type_id + entity_id. All semantics in domain.json. Swap config = new world. Degree conservation (Σ=0) thermodynamics model. · 拓扑-内容解耦 + 度守恒 | Position-as-relationship: no parent/child fields. Co-located entities are independent. Layer architecture: one abstract method per layer, YAML defines content. Hybrid async: busy-queue + inbox-messaging. · 位置即关系 + 层架构 + 混合异步 |

---

## 🏗 Architecture · 架构

```
┌──────────────────────────────────────────────────────────┐
│                    YAML Config                           │
│   world.yaml  ·  prompts.yaml  ·  llm.yaml              │
│   All behavior, text, rules. Zero Python hardcoding.     │
├──────────────────────────────────────────────────────────┤
│                    Layer System                          │
│                                                          │
│   ┌──────────┐  ┌───────────────┐  ┌─────────┐          │
│   │ Visual   │  │ Interaction   │  │ Agent   │  ...     │
│   │ Layer    │  │ Layer         │  │ Layer   │          │
│   │          │  │               │  │         │          │
│   │ see(d)   │  │ interact(act) │  │ drives  │          │
│   │ 统一接口  │  │ 统一接口       │  │ sensory │          │
│   └──────────┘  └───────────────┘  └─────────┘          │
│                                                          │
│   Each layer: one abstract method. Content from YAML.    │
│   每层一个抽象方法。内容来自 YAML。                          │
├──────────────────────────────────────────────────────────┤
│                    Entity (Container)                     │
│                                                          │
│   id + name + zone + pos + layers: dict[str, Layer]      │
│   一切皆实体。无子类。                                      │
├──────────────────────────────────────────────────────────┤
│                    Systems (Cross-Layer)                  │
│                                                          │
│   ┌──────────────┐  ┌────────────────┐  ┌──────────┐    │
│   │ Sensory      │  │ Interaction    │  │ Decay     │    │
│   │ System       │  │ System         │  │ System    │    │
│   │              │  │                │  │           │    │
│   │ read Layers  │  │ passive → LLM  │  │ drive × t │    │
│   │ → write      │  │ agent   → inbox│  │           │    │
│   │ sensory      │  │ event   → spawn│  │           │    │
│   └──────────────┘  └────────────────┘  └──────────┘    │
│                                                          │
│   Only place where cross-layer logic exists.             │
│   跨层逻辑唯一在此。Entity 不做跨层。                        │
├──────────────────────────────────────────────────────────┤
│                    Agent Loop                             │
│                                                          │
│   while alive:                                           │
│     decay()  →  sense()  →  think(LLM #1)                │
│     → move()  →  submit() / send_message()               │
│     → LLM #2 (async)  →  apply()  →  sleep(duration)     │
│                                                          │
│   ★ LLM #1: Decision · 决策                              │
│   ★ LLM #2: Resolver · 裁判 (passive entity only)        │
├──────────────────────────────────────────────────────────┤
│                    API (REST + WebSocket)                 │
│                    Frontend (Phaser.js)                   │
└──────────────────────────────────────────────────────────┘
```

---

## 🎮 Core Concepts · 核心概念

### 1. Layer Architecture · 层架构

Every entity is composed of independent layers. Each layer exposes a **single unified method** — content varies by YAML config.

每个实体由独立层组成。每层暴露**一个统一方法** — 内容由 YAML 配置决定。

```yaml
# Example: "Bar Counter" entity
实体示例："吧台"
visual:                          # Visual Layer · 视觉层
  sprite: "counter_bar"          # Rendered in frontend · 前端渲染
  info:
    look: "木制吧台，后面站着矮人老板"   # Seen from afar · 远观
    detail: "酒架上有几瓶酒"            # Seen up close · 近看

interaction:                     # Interaction Layer · 交互层
  actions:
    搭话:                         # Action name · 动作名
      resolve: llm               # LLM resolver · LLM 裁定
    倚靠:
      resolve: rule              # Engine-resolved · 引擎直接算
      rule:
        cost: {energy: -2}
        effects: {fun: 5}
```

### 2. Position = Relationship · 位置即关系

No parent/child or container relationships. Entities sharing the same coordinates coexist independently.

无父子关系、无容器。同坐标多实体各自独立。

```yaml
# A bar counter, an ale, and a wine — all at [7,2], no hierarchy
# 吧台、麦酒、葡萄酒 — 同在 [7,2]，无从属
- id: bar_counter   pos: [7, 2]
- id: drink_ale     pos: [7, 2]     # Independent entity · 独立实体
- id: drink_wine    pos: [7, 2]     # Independent entity · 独立实体
```

### 3. Hybrid Async Interaction · 混合异步交互

| | Passive Entity · 被动实体 | Agent-to-Agent · Agent 间 |
|---|---|---|
| Example · 示例 | `drink_ale.interact("饮用")` | `xiaoming.interact("交谈")` |
| Flow · 流程 | submit → busy → LLM #2 → apply | send_message → inbox → target's LLM #1 |
| Agent blocked? · Agent 阻塞？ | ✅ Busy, but can reply inbox · 仅排队，仍能回复 | ❌ Not blocked at all · 完全不阻塞 |
| Property adjudication · 属性裁定 | LLM #2 (with ambient entities) | Target's own LLM · 目标自己的 LLM |

### 4. Design Principles · 设计原则

| # | Principle · 原则 |
|---|---------|
| 1 | **Single Entity Class** — No subclasses. Difference = YAML · 唯一 Entity 类 |
| 2 | **Layer Architecture** — Independent visual/interaction/agent layers · 层独立 |
| 3 | **Flat Attributes** — `coins` equals `hunger`. All is `apply_deltas()` · 属性平权 |
| 4 | **Position = Relationship** — Co-located entities coexist independently · 位置即关系 |
| 5 | **Config as Behavior** — Prompt/interface/rule all in YAML · 配置即行为 |
| 6 | **Systems as Orchestrator** — Cross-layer logic only in Systems · Systems 总控 |
| 7 | **Agent Autonomy** — Agent-to-agent via inbox, self-determined attributes · Agent 自治 |
| 8 | **LLM Minimized** — Only 2 call points: Decision + Resolver · LLM 最小化 |
| 9 | **Frontend Agnostic** — Sprite renderer, zero world knowledge · 前端零知识 |
| 10 | **Extensible Zero-Code** — New zone/entity/action = YAML only · 扩展零代码 |

---

## 📂 Project Structure · 项目结构

```
06_AgentWorld_Async/
│
├── config/                        # 🔧 All configuration · 全部配置
│   ├── world.yaml                 #   Zones + Entities + Interfaces
│   ├── prompts.yaml               #   LLM prompts (slots + templates)
│   └── llm.yaml                   #   LLM provider config
│
├── src/                           # 🐍 Python backend · Python 后端
│   ├── layers/                    #   Layer definitions · 层定义
│   │   ├── base.py                #     Layer base class
│   │   ├── visual.py              #     VisualLayer: see(distance)
│   │   ├── interaction.py         #     InteractionLayer: interact(action)
│   │   ├── agent.py               #     AgentLayer: drives + sensory + memory
│   │   └── auditory.py            #     AuditoryLayer: hear(distance)
│   │
│   ├── entity/                    #   Entity model · 实体模型
│   │   ├── entity.py              #     Single Entity class · 唯一类
│   │   └── event_entity.py        #     EventEntity: dynamic spawn + auto-expire
│   │
│   ├── systems/                   #   Cross-layer orchestration · 跨层编排
│   │   ├── sensory.py             #     SensorySystem: perception
│   │   ├── interaction.py         #     InteractionSystem: submit + resolve_async
│   │   └── decay.py               #     DecaySystem: natural decay
│   │
│   ├── agent/                     #   Agent mind · Agent 心智
│   │   ├── brain.py               #     LLM #1 Decision engine
│   │   ├── drives.py              #     Drive system (thirst/hunger/...)
│   │   ├── memory.py              #     Short-term memory
│   │   ├── sensory_memory.py      #     Perception state
│   │   └── inbox.py               #     Async message inbox
│   │
│   ├── interaction/
│   │   └── resolver.py            #   LLM #2 Interaction resolver
│   │
│   ├── prompt/
│   │   ├── assembler.py           #   Slot-based prompt assembler
│   │   └── loader.py              #   YAML config loader
│   │
│   ├── llm/
│   │   └── client.py              #   Dual-provider LLM client
│   │
│   ├── core/
│   │   ├── world.py               #   World container + entity factory
│   │   └── clock.py               #   Simulated clock
│   │
│   └── api/                       #   API layer (REST + WebSocket)
│       ├── server.py
│       ├── routes.py
│       └── ws.py
│
├── web/                           # 🎨 Frontend · 前端 (Phaser.js)
│   ├── index.html
│   ├── js/
│   │   ├── scenes/WorldScene.js
│   │   ├── ui/HUD.js, EventLog.js
│   │   └── network/ws.js, api.js
│   └── assets/tilesets/, sprites/
│
├── SPEC.md                        # 📘 Full technical specification · 完整技术规格
├── main.py                        # 🚀 Entry point · 入口
├── requirements.txt
└── README.md                      # 📖 This file · 本文件
```

---

## 🚀 Quick Start · 快速开始

### Prerequisites · 环境要求

- Python 3.12+
- LLM API key (MiniMax or DeepSeek)

### Installation · 安装

```bash
git clone git@github.com:Asher0501/AgentWorld_Async.git
cd AgentWorld_Async

pip install -r requirements.txt
```

### Configuration · 配置

The engine auto-discovers API keys from your OpenCode/OpenClaw config. To use a specific provider:

```yaml
# config/llm.yaml
provider: "deepseek"          # deepseek | minimax
model: "deepseek-chat"
```

Or set environment variables:

```bash
export DEEPSEEK_API_KEY="sk-your-key"
# or
export MINIMAX_API_KEY="your-key"
```

### Run Demo · 运行示例

```bash
python main.py
```

**Expected output · 预期输出:**

```
⏱  14:00 | 小明 (5,5)
  💭 想下一步... (thirst=80 coins=30)
  🚶 移动到 (7,2)，耗时 5 分钟

⏱  14:02 | 小明 (7,2)
  🎯 饮用 麦酒 → 后台裁定中...

⏱  14:06 | 小明 (7,2)
  📖 小明微笑着递给矮人老板5枚硬币，端起麦酒痛快地喝了一大口...
     → 状态变化: {'coins': -5, 'thirst': -20, 'mood': 5}
     → 周边影响: [{'entity_id': '吧台', 'deltas': {'mood': 2}}]
```

---

## 🔍 Key Interactions · 关键交互

### Flow: Drinking Ale · 交互流程：喝麦酒

```
Agent LLM #1 decides:          小明 LLM #1 决策:
  "I'm thirsty. Drink ale."       "渴了，喝麦酒"
       │
       ▼
InteractionSystem.submit()      提交交互 → Agent busy
       │
       ├── Collect ambient:     收集周边实体:
       │     bar_counter (老板,mood=60)
       │     drink_wine   (葡萄酒,price=12)
       │
       ├── LLM #2 Resolver:     LLM #2 裁定:
       │     caller:  thirst=80, coins=30
       │     target:  price=5
       │     ambient: 老板在场
       │     → coins: -5, thirst: -20, mood: +5
       │     → 老板 mood: +2
       │
       └── Apply + EventEntity spawn
              广播: "小明在吧台前喝了一口麦酒"
```

### Flow: Agent Chatting · 交互流程：Agent 聊天

```
Agent A (老王):                Agent B (小明):
  think: "找小明聊天"              (正在喝东西, busy)
       │                           │
  send_message(小明.inbox) ──→   inbox 收到消息
       │                           │
  sleep                              think (busy 中仍能 think):
       │                              "回复老王: 哟!"
       │                              send_message(老王.inbox)
       │                              mood +5 (自己的 LLM 决定)
       │                           │
  inbox 收到回复                      sleep
  think: "聊得不错"
  mood +8 (自己的 LLM 决定)
```

---

## 🧩 Extending · 扩展

### Add a new zone · 新增区域

```yaml
# config/world.yaml
zones:
  - id: shop_zone
    name: "杂货铺"
    width: 12
    height: 10
    # + tilemap + connections
```
**Zero code changes. · 代码零改动。**

### Add a new entity · 新增实体

```yaml
entities:
  - id: bread
    zone: shop_zone
    pos: [5, 3]
    visual:
      sprite: null
      info: {look: "一条刚出炉的面包"}
    interaction:
      actions:
        购买:
          target_type: passive
          resolve: llm
```
**Zero code changes. · 代码零改动。**

### Add a new action · 新增动作

```yaml
actions:
  品尝:               # Just add here · 只需在此添加
    target_type: passive
    resolve: rule
    rule:
      effects: {hunger: -15}
      narrative: "{caller}咬了一口面包"
```
**Zero code changes. · 代码零改动。**

---

## 🛠 Technical Stack · 技术栈

| Layer · 层 | Technology · 技术 |
|---|---|
| Runtime · 运行时 | Python 3.12 + asyncio |
| LLM · 大模型 | MiniMax M2.7 / DeepSeek Chat |
| HTTP Server · 服务 | FastAPI + WebSocket |
| Frontend · 前端 | Phaser.js 3 (2D pixel art) |
| Config · 配置 | YAML |
| Persistence · 存储 | SQLite (planned · 计划中) |

---

## 📋 Roadmap · 路线图

| Phase · 阶段 | Feature · 功能 | Status · 状态 |
|---|---|---|
| 0 | Single agent demo · 单 Agent 示例 | ✅ Complete |
| 1 | Multi-agent inbox interaction · 多 Agent 交互 | 🔨 In Progress |
| 2 | Persistence & knowledge system · 持久化 + 知识系统 | 📋 Planned |
| 3 | REST API + WebSocket · API 层 | 📋 Planned |
| 4 | Phaser.js pixel frontend · 像素风前端 | 📋 Planned |
| 5 | Full world config + tilemaps · 完整世界配置 | 📋 Planned |

---

## 📄 License · 许可证

MIT

---

## 📊 Deep Evaluation · 深入评价

### AgentWorld v1 — The Graph-First Production Engine

**What it does exceptionally well:**

1. **Topology-content decoupling is genuinely innovative.** The engine kernel operates on abstract `type_id` integers and `entity_id` strings — it never references entity names or types in its core logic. `domain.json` and `node_config.json` inject all semantics from outside. This means swapping these two files creates a completely new world with zero Python code changes. I have not seen this degree of domain-agnosticism in any other LLM-agent framework.

2. **Graph as single source of truth.** Every entity is a node; every relationship is an edge with a quantity. Inventory is not a separate table — it IS the npc→item edges. Zone membership IS npc→zone edges. There is no possible inconsistency between "inventory" and "graph" because they are the same thing. The `supply_view()` recursive aggregation and `build_components()` BFS traversal are elegant uses of graph theory for practical simulation needs.

3. **Conservation validation (Σ=0) is a smart constraint.** Inspired by thermodynamics, it distinguishes internal transfers (must conserve) from system-boundary flows (consumption, gathering — may not). Items marked `is_conserved: true` (coins, herbs, weapons) participate in checks; consumable-from-environment items don't. The group-based conservation means one unbalanced trade doesn't pollute another. This is well-thought-out.

4. **Verification registry with feedback retry.** The 8-check system with mask-based activation per layer is clean architecture. The retry loop that builds structured feedback from `CheckFailure` objects (with error codes, fix hints, and the LLM's previous raw output) is exactly how you should do LLM output correction — give it the exact failing JSON and tell it what's wrong, not "try again."

5. **Production-grade batch execution.** `run_50ticks.py` running each tick as a subprocess with 20-minute timeout, 2 retries, idempotent skip-check (checks for existing REPORT.md), and regex-based stdout metric extraction — this is battle-ready batch processing. The contextvars-based parallel tracing instrumentation is sophisticated.

**What it struggles with:**

1. **Global tick lockstep kills emergence.** All 13 NPCs act simultaneously every tick. An NPC cannot react to another NPC's action within the same tick — reactions always lag by one tick. This fundamentally limits causal chain simulation: if Geralt enters the tavern, Dandelion can't greet him until the next tick. The world feels like a sequence of still frames, not a living flow.

2. **LLM output is rigid structured ops.** The LLM must output `{"op":"delta","src":"npc_97845b74","tgt":"item_coin","delta":-5}` — a machine-readable graph operation. This is elegant from an engine perspective but constraining from an LLM perspective. The LLM cannot express nuance like "negotiate the price" or "leave without paying because the bartender is asleep." Everything reduces to quantity deltas.

3. **Graph edges are semantically overloaded.** Edge types carry implicit meaning (`npc_zone`, `npc_item`, `zone_zone`, etc.) hardcoded in Python. Adding a new relationship type (e.g., `npc_owes_debt_to`) requires code changes in multiple places. The graph engine is domain-agnostic for nodes but domain-aware for edges.

4. **Prompt assembly is split across code and config.** The adapter has 30+ `slot_*` methods that format templates from `domain.json`, but the slot definitions and their ordering live in `adapter.py`. Adding a new prompt requires touching Python (to define the template) AND JSON (to define the slot content). It's not purely config-driven.

5. **NPCs have no internal drives.** Behavior is entirely prompt-driven: LLM #1 receives a slot-injected prompt with npc_state, surroundings, and decision guidance, then outputs a plan. An NPC doesn't "feel thirsty" — it's just told its vitality/satiety/mood numbers and expected to make a plan. This is efficient but lacks the bottom-up drive model that creates surprising behavior.

---

### AgentWorld Async (v2) — The Layer-Architected Autonomy Sandbox

**What it does exceptionally well:**

1. **Position-as-relationship is philosophically clean.** By removing all parent/child/container semantics and making spatial co-location the only implicit relationship, the architecture eliminates an entire class of coupling. A drink on a bar counter is just two entities at [7,2] — no `owner_id`, no `parent_entity`, no `inventory` mapping. Move the drink to [3,5] and it's "on the table" with zero code changes. This is genuinely elegant.

2. **Layer architecture with unified interfaces.** Each layer exposes ONE method (`see()`, `interact()`, `hear()`) — the code defines the signature, YAML defines the return values. This means adding a new entity type or action requires zero Python changes. The InteractionLayer's action names ("饮用", "搭话", "倚靠") are plain strings from YAML, not Python method names. The LLM sees human-readable action lists, not method signatures.

3. **LLM as judge, not graph-op generator.** The resolver (LLM #2) sees private attributes of both parties + ambient entities, then outputs a narrative + attribute deltas. This is more natural for LLMs than structured graph operations. It allows nuanced outcomes: "偷喝" (drink without paying) results in `{thirst: -20, bar_counter.mood: -8}` — the LLM understood social context, not just graph quantity changes.

4. **True agent autonomy via inbox.** Agent-to-agent interactions go through async inbox messages, not through the resolver. Each agent's own LLM decides how the interaction affects its attributes. This prevents the "你的属性被我外部裁定" problem — in v1, a resolver's output could change both parties. In v2, you control your own mood changes.

5. **Hybrid async with busy/idle states.** The busy-queue model (agent is "busy" during an action but can still receive + reply to inbox messages) mirrors real-world behavior: you can't walk away mid-drink, but you can nod at someone who says hello.

6. **Pure YAML config.** All prompt text, slot definitions, action rules, entity attributes, zone definitions, and tilemaps live in YAML. The Python code contains zero hardcoded prompt strings. This is the north star of config-driven design.

7. **Three-mode interaction dispatch.** `resolve=rule` (engine-computed), `resolve=llm` (LLM judge), `target_type=agent` (inbox). All from a single YAML field. The InteractionSystem dispatches to the right code path without the caller knowing which mode is used.

**What it struggles with:**

1. **No formal verification.** v1's 8-check registry with conservation validation is absent in v2. The LLM #2 resolver is expected to produce valid outputs, but there's no `capacity_upper_bound` check, no `entity_existence` validation, no degree conservation. Attribute clamping exists but is purely numerical — it can't detect semantic errors like "LLM charged 5 coins but agent only has 3."

2. **No graph model for relationships.** Position-as-relationship works for local interactions but can't express persistent non-spatial relationships. If Geralt "owes a favor to" Dandelion, there's no way to represent this except as a `private_attrs` note — which the LLM might not consistently read. v1's graph edges with semantic types (`npc_debt_to`) would handle this naturally.

3. **Scale is demo-level.** One agent, one zone, five entities, five interactions. The architecture shows promise but hasn't been tested at scale: 10+ agents with overlapping interaction radii, 50+ simultaneous LLM calls, memory/performance under sustained multi-agent load.

4. **EventEntity lifecycle not battle-tested.** Dynamic event spawn with auto-expiry is a clever idea but hasn't been tested with concurrent observers, rapid spawn/despawn cycles, or edge cases like event entities overlapping the same coordinates.

5. **No persistence layer.** The demo runs in-memory. v1's unified `nodes` table with upsert semantics, self-seeding, and `sync_graph_to_nodes()` is a proven persistence model that v2 hasn't adopted.

6. **External API is young.** The REST + WebSocket layer works for basic move/interact/sensory operations, but doesn't yet support streaming LLM output, handling agent disconnection/reconnection, or concurrent access to the same entity.

---

### Synthesis · 综合评价

These two projects represent fundamentally different philosophies:

**v1 is a simulation engine for researchers and world-designers.** It optimizes for correctness, determinism, reproducibility (batch runs with REPORT.md), and domain portability (swap two JSON files = new world). Its graph model and conservation validator are mathematically rigorous. Its tick-synchronous model is good for studying system-level dynamics over 50+ ticks. The codebase is heavy but disciplined — 1400-line adapters, 1100-line graph engines, contextvars instrumentation, subprocess isolation. This is production code for a specific use case: running and analyzing Witcher-world simulations at scale.

**v2 is an agent autonomy sandbox for builders and tinkerers.** It optimizes for expressiveness (LLM narrates, not graph-ops), extensibility (add entity/action in YAML), and real-time interaction (async loop, WebSocket). Its layer architecture and position-as-relationship make it trivial to prototype new worlds. The hybrid async model (busy-queue + inbox) is conceptually richer than pure-turn-based or pure-async. But it lacks the rigor of v1 — no formal verification, no graph model, no persistence. The codebase is lean — ~30 files averaging ~50 lines each — but has the roughness of a prototype.

**If I were building a multi-agent platform for production:** I would take v1's graph engine + verification registry + persistence, and merge it with v2's layer architecture + YAML config + agent autonomy + hybrid async. The graph provides rigorous relationship modeling; the layers provide clean separation of concerns; YAML config provides extensibility; async provides reactivity. Neither project alone is the complete answer — but together they sketch the architecture of a truly capable multi-agent simulation engine.

**If I were an LLM-agent researcher:** v1 is the more interesting codebase to study. Its topology-content decoupling, degree conservation, and 8-check verification with feedback retry are novel contributions that most LLM-agent frameworks lack. v2's ideas (position-as-relationship, layer architecture, LLM judge) are architecturally innovative but need v1's rigor to become production-ready.

---

<p align="center">
  <sub>Built with ❤️ by Asher · 2026</sub>
</p>
