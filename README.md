<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/async-asyncio-purple" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20%7C%20OpenAI-green" alt="LLM">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="License">
</p>

<h1 align="center">
  🏠 AgentWorld Async
</h1>

<p align="center">
  <b>Observing-Driven, Layer-Architected, LLM-Powered Multi-Agent Autonomous World Engine</b><br/>
  <b>观察驱动 · 分层架构 · LLM 驱动的多智能体自主世界引擎</b>
</p>

<p align="center">
  <i>"Every entity observes the world. KL divergence triggers decisions. No fixed loop, no polling firehose."</i><br/>
  <i>"每个实体观察世界。变化触发决策。无固定节奏，无轮询风暴。"</i>
</p>

---

## 📖 Overview · 概述

**AgentWorld Async** is a multi-agent simulation engine where agents **observe the world continuously** and only **decide when something changes**. Unlike traditional turn-based or fixed-interval systems, each agent maintains layered KL divergence snapshots (auditory / visual / state) — and fires a decision only when the world around it has meaningfully shifted.

**AgentWorld Async** 是一个多智能体仿真引擎。Agent **持续观察世界**，仅在变化发生时决策。告别回合制或固定间隔——每个 Agent 维护分层 KL 散度快照（听觉/视觉/状态），世界真正变化时才触发 LLM。

### 🆚 Architecture Evolution · 架构演进

| Version | Model | Decision trigger | LLM calls/interaction |
|---------|-------|:-----------------:|:--------------------:|
| v2 | submit → LLM #2 resolver → busy_result poll | Fixed loop | 4 (decide + 2 proj + memory) |
| v3 | v3 pipeline (story + per-agent projection) | Fixed loop | 4 |
| **Current** | **observing baseline + layered KL** | **KL divergence triggers** | **1-2 (decide ± interact_narrative)** |

---

## 🏗 Architecture · 架构

```
┌──────────────────────────────────────────────────────────────┐
│                      config/                                  │
│   world.yaml  ·  prompts.yaml  ·  llm.yaml                    │
│   All behavior, all text, all rules. Zero Python hardcoding.  │
├──────────────────────────────────────────────────────────────┤
│                      Layer System                             │
│                                                                │
│   ┌──────────┐  ┌───────────────┐  ┌─────────┐  ┌─────────┐  │
│   │ Visual   │  │ Interaction   │  │ Agent   │  │Auditory │  │
│   │ Layer    │  │ Layer         │  │ Layer   │  │ Layer   │  │
│   │          │  │               │  │         │  │         │  │
│   │ look +   │  │ actions dict  │  │ drives  │  │current_ │  │
│   │express   │  │ (plain dict)  │  │ sensory │  │speech   │  │
│   └──────────┘  └───────────────┘  └─────────┘  └─────────┘  │
│                                                                │
│   Observers poll these layers. No push. No EventBus.           │
│   观察者轮询读取。无推送。无事件总线。                            │
├──────────────────────────────────────────────────────────────┤
│                      Entity (Container)                        │
│                                                                │
│   id + name + zone + pos + layers: dict[str, Layer]            │
│   + KL snapshots: p_auditory, p_visual, p_state, p_stale      │
│   一切皆实体。无子类。KL 快照内嵌。                               │
├──────────────────────────────────────────────────────────────┤
│                      Systems                                   │
│                                                                │
│   ┌──────────────┐  ┌────────────────┐  ┌──────────┐          │
│   │ Sensory      │  │ Interaction    │  │ Decay     │          │
│   │ System       │  │ System         │  │ System    │          │
│   │              │  │                │  │           │          │
│   │ poll Layers  │  │ interact()     │  │ drive×t   │          │
│   │ → vision     │  │ sole entry     │  │           │          │
│   │ → hearing    │  │ point          │  │           │          │
│   └──────────────┘  └────────────────┘  └──────────┘          │
├──────────────────────────────────────────────────────────────┤
│                      Agent Loop                                │
│                                                                │
│   while:                                                        │
│     sensory.poll → layered KL → KL empty? → sleep(0.3)        │
│                    KL non-empty?       → decide(LLM #1)       │
│     → speak(NPC) or invoke(Item) → observing                  │
│     → observing: poll → target replied? → decide(有上下文)     │
│                     → target ignored? → decide("那算了")       │
│                                                                │
│   ★ LLM #1: Decide (1 call/interaction)                        │
│   ★ LLM #2: interact_narrative (only for NPC→Item)             │
├──────────────────────────────────────────────────────────────┤
│                      API (REST + WebSocket)                    │
│                      Frontend (Phaser.js)                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎮 Core Concepts · 核心概念

### 1. Observing Baseline · 观察基线

Agents don't decide on a timer. They observe continuously. KL divergence across four layers determines when to act.

Agent 不定时决策。持续观察世界。四层 KL 散度决定何时行动。

```
听觉 KL: speech_ts 变化 → "X 说了新的话"
视觉 KL: 实体进出范围 / zone变化 / 表情变化
状态 KL: drives cross 阈值 (30/60/80)
时差 KL: >30s 无动作 → "太久没事做了"

总 KL = 四分量并集。非空→decide。空→继续观察。
```

### 2. Unified interact() · 统一交互

Single entry point. All interactions go through `interact()`.

```python
interact(agent, target, action_name, decision):
    ① agent.auditory.current_speech = decision.dialogue    ← 对方 poll 读到
    ② agent.visual.expression       = decision.visual
    ③ agent.apply_deltas(decision.self_deltas)
    ④ if target.is_agent: return                            ← NPC→NPC: 0 extra LLM
    ⑤ if target.is_item:  interact_narrative LLM            ← NPC→Item: +1 LLM
    ⑥ if gate: world.transfer_zone()
```

### 3. Layered KL · 分层 KL

Each agent maintains independent P/Q snapshots per layer.

| Layer | P | Q | Trigger rule |
|-------|---|---|--------------|
| Auditory | last poll speaker_ids | current poll | new speaker OR speaker left range |
| Visual | last poll entity_ids + expressions | current poll | entity enter/leave OR expression change |
| State | last poll drives snapshot | current drives | cross threshold (30/60/80) only |
| Stale | last decide time | now | >30s gap |

### 4. LLM Output · LLM 输出

```json
{
  "action": "走向特莉丝问诺维格瑞的事",
  "story": "...",
  "dialogue": "诺维格瑞出什么事了？",
  "visual": "目光锐利，手指敲着桌沿",
  "internal": "她在隐瞒什么",
  "self_deltas": {"social": 3, "mood": -2},
  "expects_reply": true,
  "patience": 8
}
```

### 5. World Config · 世界配置

All entities defined with `description` + per-action `description`. No `resolve`, `rule`, `effects`, `cost`.

```yaml
- id: square_well
  name: 水井
  description: "广场中央的石砌水井。井沿被无数只手磨得光滑。"
  interaction:
    actions:
      打水:
        description: "放下木桶，摇辘轳打水。井水地下暗河，常年清凉甘甜。"
      看:
        description: "低头往井里看。深不见底，隐约能听到水声。"

- id: square_bar_gate
  name: 酒馆入口
  interaction:
    actions:
      进入酒馆:
        description: "推开橡木门走进去。麦酒和烤肉的气味扑面而来。"
        gate: {to_zone: bar_zone, to_pos: [1,4]}
```

### 6. Design Principles · 设计原则

| # | Principle · 原则 |
|---|---------|
| 1 | **Observing Baseline** — Agents watch, don't poll on a timer · 观察基线 |
| 2 | **KL-Driven Decisions** — Layer diff triggers action, not clock · KL 触发 |
| 3 | **Single interact()** — One entry point, no submit/resolver chain · 统一入口 |
| 4 | **Layer Architecture** — Independent layers, observers poll · 层独立 |
| 5 | **Position = Relationship** — Co-located entities coexist independently · 位置即关系 |
| 6 | **Config as Behavior** — All behavior in YAML, zero hardcoded Python · 配置即行为 |
| 7 | **Agent Autonomy** — B answers via its own decide(), not projector · Agent 自治 |
| 8 | **LLM Minimized** — 1-2 calls/interaction · LLM 最小化 |
| 9 | **Frontend Agnostic** — Sprite renderer, zero world knowledge · 前端零知识 |
| 10 | **Extensible Zero-Code** — New entity/action = YAML only · 扩展零代码 |

---

## 📂 Project Structure · 项目结构

```
06_AgentWorld_Async/
│
├── config/
│   ├── world.yaml        # Zones + Entities + Actions (description-only)
│   ├── prompts.yaml      # agent_decision + interact_narrative templates
│   └── llm.yaml          # LLM provider config
│
├── src/
│   ├── layers/
│   │   ├── base.py       # Layer base class
│   │   ├── visual.py     # VisualLayer: properties dict (look, expression)
│   │   ├── interaction.py # InteractionLayer: actions dict[str, dict]
│   │   ├── agent.py      # AgentLayer: drives + sensory + memory
│   │   └── auditory.py   # AuditoryLayer: properties dict (current_speech)
│   │
│   ├── entity/
│   │   ├── entity.py     # Single Entity: + KL snapshots + observing fields
│   │   └── event_entity.py
│   │
│   ├── systems/
│   │   ├── sensory.py    # SensorySystem: update() — poll vision+hearing; write hearing→memory
│   │   ├── interaction.py # InteractionSystem: interact() sole entry, +5 helpers
│   │   └── decay.py      # DecaySystem
│   │
│   ├── agent/
│   │   ├── brain.py      # Brain: decide() + extract_json()
│   │   ├── drives.py     # DriveSystem
│   │   ├── memory.py     # AgentMemory {ts, text}
│   │   ├── sensory_memory.py # VisionRecord, HearingRecord, SensoryMemory
│   │   └── inbox.py
│   │
│   ├── prompt/
│   │   ├── assembler.py  # Slot-based prompt assembler
│   │   └── loader.py     # YAML config loader
│   │
│   ├── llm/
│   │   └── client.py     # LLM client (OpenAI/DeepSeek, timeout 120s)
│   │
│   ├── core/
│   │   ├── world.py      # World container + entity factory
│   │   ├── clock.py      # Simulated clock
│   │   ├── lifecycle.py  # EntityLifecycle: spawn/despawn/transfer_zone
│   │   ├── spatial_grid.py # O(1) spatial queries
│   │   ├── error_collector.py
│   │   └── kl_divergence.py # KL divergence compute (to be layered)
│   │
│   └── api/
│       ├── server.py
│       ├── routes.py
│       └── ws.py
│
├── test_e2e_concurrent.py # Main test: observing + layered KL
├── main.py                # Entry point
├── requirements.txt
└── README.md
```

**Deleted · 已删除**: `resolver.py` (LLM #2-#4 chain), `event_bus.py` (unused pub/sub)

---

## 🚀 Quick Start · 快速开始

```bash
pip install -r requirements.txt
cp config/llm.yaml.example config/llm.yaml  # configure API key
python main.py                               # API server + demo
python test_e2e_concurrent.py                # 8-agent concurrent test
```

---

## 🔍 Key Interactions · 关键交互

### NPC→NPC: A speaks, B hears, B decides

```
A.decide() → "诺维格瑞出什么事了？" expects_reply=true patience=8
interact():
  A.auditory.current_speech = "诺维格瑞出什么事了？"      ← B 下轮 poll 读到
  A.visual.expression       = "目光锐利"
  A.apply_deltas({social:3})
  → A 进入 observing

B's loop:
  poll → sensory.hearing["geralt"] = "诺维格瑞出什么事了？"
        → memory.record → auditory KL = "杰洛特 说话了" → trigger → decide
        → "不关你的事" → B.auditory → A 下轮 poll 听到 → observing 结束
        → A's next decide: "他回了。追问。"
```

### NPC→Item: A interacts, LLM narrates

```
A.decide() → "打水喝" self_deltas={thirst:-25}
interact():
  → interact_narrative LLM:
    prompt: "杰洛特对水井执行了打水。井深不见底，井水来自地下暗河..."
    → {narrative: "杰洛特摇辘轳，清凉井水涌出...", deltas: {thirst:-28}}
```

---

## 📋 Update Log · 更新记录

### May 2026 — Architecture v4

| Change | Detail |
|--------|--------|
| **Observing baseline** | Agents watch continuously; KL triggers decide |
| **Layered KL** | Auditory / visual / state / stale — independent P/Q per layer |
| **Unified interact()** | Single entry point; deleted submit, _resolve_v3, resolver chain |
| **Deleted LLM #2-#4** | Removed projection engine, memory writer, resolver. NPC→NPC: 1 LLM call. |
| **Deleted EventBus** | Observers poll layers directly; no push/broadcast |
| **Deleted busy_until/busy_result** | No fixed busy. LLM outputs `expects_reply` + `patience`. |
| **World config simplified** | Removed `resolve/rule/effects/cost`. Entities use only `description` + `actions.description`. |
| **Auditory layer** | All agents have `auditory` layer; observers poll `properties.current_speech` |
| **Hearing→memory** | First-time hearing auto-saved to memory for long-term retention |
| **LLM output extended** | Added `self_deltas`, `expects_reply`, `patience` fields |
| **Memory unstructured** | `{ts, text}` format; deleted `record_fail` |
| **Layer properties** | `info` → `properties: dict` for extensible JSON |
| **Deleted files** | `resolver.py`, `event_bus.py`, 5× `.bak` |

---

## 📄 License · 许可证

MIT
