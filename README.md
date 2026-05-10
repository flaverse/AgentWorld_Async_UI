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

## 📊 Evaluation · 项目评价

For a comprehensive bilingual deep evaluation comparing v1 and v2, see **[EVALUATION.md](EVALUATION.md)**.

完整的中英双语深入评价见 **[EVALUATION.md](EVALUATION.md)**。

---

<p align="center">
  <sub>Built with ❤️ by Asher · 2026</sub>
</p>
