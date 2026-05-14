<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v4-ff6b35?style=flat-square" alt="v4">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License">
</p>

<h1 align="center">🏠 AgentWorld Async</h1>

<p align="center">
  <b>P/Q/KL-Driven · Layer-Architected · LLM-Powered</b><br/>
  <b>Multi-Agent Autonomous World Engine</b>
</p>

<p align="center">
  <i>The world doesn't change — the agent doesn't think.</i><br/>
  <i>世界不变化，Agent 不思考。</i>
</p>

---

## 🆚 vs Similar Projects · 与同类项目对比

| | Generative Agents<br/><sub>Park et al. 2023</sub> | CrewAI / AutoGen | **AgentWorld Async** |
|---|---|---|---|
| **Decision trigger** | Fixed-interval reflection | Tool-calling pipeline | **P/Q/KL attention gate** — event-driven |
| **LLM calls / interaction** | 3+ (plan + reflect + act) | 1 per tool call | **1** (NPC→NPC), **2** (NPC→Item) |
| **Agent-to-agent** | One-way observation | Message-passing | **Mutual observation** — A writes blackboard, B polls |
| **Personality** | Prompt only | Prompt only | **LLM #1 output drives behavior** — no proxy projection |
| **Config** | Code + JSON | Python decorators | **Pure YAML** — description-only, zero code changes |
| **Memory** | Reflection-based summary | Chat history | **Full decision JSON** — agent remembers everything |
| **Architecture** | Monolithic agent loop | Distributed agents | **Layer-based container** — visual/auditory/interaction |
| **World scale** | 25 agents, 2 days | N/A | 3 zones, 23 entities — **zero-hardcode switchable** |

### Key Innovations · 核心创新

| # | Innovation | Why It Matters |
|---|-----------|----------------|
| 1 | **P/Q/KL Attention Gate** | 4-channel parallel diff (auditory/visual/state/temporal). Agent only calls LLM when world actually changes. 0.3s polling replaces fixed-interval loops. |
| 2 | **Write-Pending Lock** | After interacting, agent yields exactly one poll cycle. Disrupted conversations self-repair without fixed timers. |
| 3 | **Unified `interact()`** | NPC→NPC and NPC→Item share one code path. B answers via its own `decide()` — no proxy projection engine. |
| 4 | **Layer Architecture** | Visual/Auditory/Interaction layers independently defined. Observers poll — no EventBus, no push, no gossip protocol needed. |
| 5 | **Config-as-Behavior** | Every string, threshold, currency key, and drive limit injected from YAML. Swap `world.yaml` = new world. Zero Python changes. |
| 6 | **Full Decision Memory** | Entire LLM #1 output (dialogue, visual, internal, self_deltas, story, expects_reply, patience) recorded as JSON. Agent remembers what it said, did, and felt. |
| 7 | **Observing Baseline** | Default state is observation. Decisions are triggered by change — not by a timer. "The world pushes the agent, not the other way around." |

---

## 🏗 Architecture

```
┌──────── config/ ────────┐    ┌──── entity ──────────────────┐
│ world.yaml · prompts.yaml│    │  Entity: id name zone pos    │
│ llm.yaml                 │    │  layers: {visual, auditory,  │
│ All behavior in YAML.    │    │           interaction, agent} │
│ Zero Python hardcoding.  │    │  + P/Q KL snapshots          │
└──────────────────────────┘    │  + _write_pending lock       │
                                │  + observing state            │
┌──── layers ────┐              └──────────────────────────────┘
│ Visual         │
│  · see(d) →    │              ┌──── KL Gate ──────────────────┐
│    look+detail │              │  auditory │ visual │ state    │
│                │              │    P→Q       P→Q     P→Q     │
│ Auditory       │              │    ε_a   OR  ε_v  OR ε_s  OR ε_t│
│  · hear(d) →   │              │           ↓                   │
│    speech+vol  │              │      total_KL ≠ ""            │
│                │              │           ↓                   │
│ Interaction    │              │      trigger decide           │
│  · actions:dict│              └───────────────────────────────┘
│  · apply(d)    │                          │
└────────────────┘              ┌───────────┴───────────────────┐
                                │       brain.decide()  ← 1 LLM │
┌──── systems ────┐             │  { action, dialogue, visual,  │
│ SensorySystem   │             │    internal, self_deltas,     │
│  · poll vision  │             │    expects_reply, patience }  │
│  · poll hearing │             └───────────┬───────────────────┘
│  · hearing→mem  │                         │
│                 │             ┌───────────┴───────────────────┐
│ InteractionSys  │             │        interact()             │
│  · interact()   │             │  ① A.auditory = dialogue      │
│  · fuzzy_match  │             │  ② A.visual   = expression    │
│  · check_observe│             │  ③ A.apply_deltas(self)       │
│                 │             │  ④ _write_pending = True      │
│ DecaySystem     │             └───┬──────────────┬────────────┘
│  · drive × t    │                 │              │
└─────────────────┘            target.is_agent  target.is_item
                                    │              │
                              return (0 LLM)  +narrative LLM (1)
                                    │
                              A → observing (expects_reply)
                              B polls → hears A → B.decide()
```

---

## 🧠 P/Q/KL Gate

```
P = Last poll's sensory latch (agent's internal prediction)
Q = Current poll's sensory input (the world as it is)
ε = Threshold-gated |Q - P| (prediction error)

┌──────────┬──────────────────┬──────────────────┬───────────────────────┐
│ Channel  │ P (last latch)   │ Q (current poll) │ Trigger condition      │
├──────────┼──────────────────┼──────────────────┼───────────────────────┤
│ Auditory │ speaker_ids      │ hearing dict     │ speech_ts changed OR   │
│          │                  │                  │ speaker left range     │
│ Visual   │ entity_ids       │ vision dict      │ entity enter/leave OR  │
│          │ + expressions    │                  │ expression changed     │
│ State    │ drives snapshot  │ current drives   │ any drive crosses      │
│          │                  │                  │ {30, 60, 80}           │
│ Temporal │ last decide time │ now              │ idle > 30s             │
└──────────┴──────────────────┴──────────────────┴───────────────────────┘

KL_total = join_if_any([KL_a, KL_v, KL_s, KL_t])
  "" → continue observing (sleep 0.3s)
  !="" → trigger decide()
```

---

## 🔄 Agent Loop

```
          ┌──────────────┐
          │   observing   │ ← baseline, no LLM
          └──────┬───────┘
                 │ sensory.poll + decay.tick (every poll_interval)
                 ▼
          ┌─────────────┐
          │  compute KL  │
          └──┬───────┬───┘
             │       │
         KL=""   KL≠""
             │       │
             ▼       ▼
         sleep    ┌──────────────┐
         poll     │ check        │
                  │ observing    │── replied/left/timeout → back to KL
                  │ (if expects  │
                  │  _reply)     │
                  └──────┬───────┘
                         │ resolved
                         ▼
                  ┌─────────────┐
                  │  decide()    │ ← ① LLM
                  └──────┬──────┘
                         ▼
                  ┌──────────────┐
                  │  _write_     │── True → release + sleep poll
                  │  pending?    │
                  └──────┬───────┘
                         │ False
                         ▼
                  ┌─────────────┐
                  │  interact()  │
                  │  + observing │
                  └─────────────┘
```

---

## 🎮 interact() — Unified Entry

```
interact(A, target, action_name, decision)

  ① A.auditory["current_speech"] = decision.dialogue
        → B polls → sensory.hearing[A]

  ② A.visual["expression"] = decision.visual
        → B polls → sensory.vision[A]

  ③ A.apply_deltas(decision.self_deltas)
        → thirst -28, mood +3

  ④ agent.memory.record(json.dumps(decision))
        → full multimodal memory retention

  ⑤ A._write_pending = True
        → yield next poll cycle

  ⑥ if target.is_agent → return                    (NPC→NPC: 0 extra LLM)
     if target.is_item  → interact_narrative LLM    (NPC→Item: 1 extra LLM)
     if gate → world.transfer_zone()
```

| Scenario | LLM calls |
|----------|:--------:|
| Observing (idle) | **0** |
| NPC→NPC conversation | **1** |
| NPC→Item interaction | **2** |

---

## 📐 Design Principles

| # | Principle | Summary |
|---|-----------|---------|
| 1 | **P/Q/KL Driven** | World changes → agent decides. Not a timer. |
| 2 | **Observing Baseline** | Default state is observation. Decisions are rare. |
| 3 | **Single interact()** | One entry point. No submit/resolver/projection chain. |
| 4 | **Layer Architecture** | Each layer exposes one method. Observers poll. |
| 5 | **Agent Autonomy** | B answers via own decide(). No proxy projection. |
| 6 | **Config as Behavior** | All text/thresholds/currencies in YAML. Zero Python hardcode. |
| 7 | **LLM On-Demand** | 1 call for NPC→NPC. 2 for NPC→Item. Maximum. |

---

## 📂 Structure

```
AgentWorld_Async/                # 24 source files · ~2000 lines
├── config/
│   ├── world.yaml               # Entities + zones + simulation params
│   ├── prompts.yaml              # Templates + slots + text_labels
│   └── llm.yaml                  # LLM provider config
├── src/
│   ├── layers/                   # Layer definitions (5 files)
│   │   ├── visual.py             #   properties: {look, expression}
│   │   ├── auditory.py           #   properties: {current_speech}
│   │   ├── interaction.py        #   actions dict + apply_deltas
│   │   └── agent.py              #   drives + sensory + memory
│   ├── entity/                   # Entity model (2 files)
│   │   └── entity.py             #   +KL snaps + observing + write-pending
│   ├── systems/                  # Cross-layer orchestration (3 files)
│   │   ├── sensory.py            #   poll vision+hearing, hearing→memory
│   │   ├── interaction.py        #   interact() + check_observing()
│   │   └── decay.py              #   drive × t
│   ├── agent/                    # Agent mind (5 files)
│   │   ├── brain.py              #   decide() + extract_json()
│   │   ├── drives.py             #   DriveSystem (currency-key-aware)
│   │   ├── memory.py             #   AgentMemory {ts, text}
│   │   └── sensory_memory.py     #   Vision/Hearing record + to_prompt
│   ├── core/                     # Engine core (5 files)
│   │   ├── world.py              #   World container + entity factory
│   │   ├── kl_divergence.py      #   4-channel P/Q KL with text injection
│   │   ├── lifecycle.py          #   EntityLifecycle
│   │   ├── spatial_grid.py       #   O(1) proximity queries
│   │   └── clock.py              #   Simulated clock
│   ├── llm/client.py             # LLM client (OpenAI / DeepSeek)
│   ├── prompt/                   # Prompt assembly (2 files)
│   │   ├── assembler.py          #   Slot + condition rendering
│   │   └── loader.py             #   YAML config loader
│   └── loop.py                   # Agent loop (single run_agent())
├── main.py                       # Entry point
├── requirements.txt
└── README.md
```

---

## 🌍 World Config

```yaml
# No resolve. No rule. No effects. Only descriptions.
# LLM reads the description and decides what happens.

- id: square_well
  name: 水井
  description: "广场中央的石砌水井。井沿被无数只手磨得光滑。"
  interaction:
    actions:
      打水:
        description: "放下木桶，摇辘轳打水。井水地下暗河，常年清凉甘甜。"

- id: geralt
  name: 杰洛特
  is_agent: true
  personality: "利维亚的杰洛特，狼学派猎魔人。寡言少语，行事果断。"
  description: "白发猎魔人，猫眼，脸上有疤。背着银剑和钢剑。"
  interaction:
    actions:
      交谈:
        description: "压低声音聊两句。杰洛特说话不多但每句都精准。"
      拍肩膀:
        description: "拍拍他的肩膀打招呼。他会抬头看一眼，继续喝他的酒。"
```

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
cp config/llm.yaml.example config/llm.yaml
python main.py                         # 8-agent concurrent (60s)
python main.py --runtime 180 --validate  # 3min + validation
```

---

## 📋 Update Log

| Version | Date | Milestone |
|---------|------|-----------|
| **v4** | May 2026 | P/Q/KL gate + observing baseline + write-pending lock |
| | | Unified interact(). Config decoupling. Full memory retention. |
| | | Delete resolver/event_bus. LLM calls: 4→1. Net code: -24000 lines. |
| v3 | Apr 2026 | Story-first pipeline + per-agent projection + verify |
| v2 | Mar 2026 | Multi-agent async: inbox messaging, hybrid busy-queue |
| v1 | Feb 2026 | Single-agent demo with graph-based world model |

---

## 📄 License

MIT
