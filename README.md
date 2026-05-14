<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20%7C%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/architecture-v4-ff6b35?style=flat-square" alt="v4">
</p>

<h1 align="center">
  🏠 AgentWorld Async
</h1>

<p align="center">
  <b>P/Q/KL-Driven · Layer-Architected · LLM-Powered</b><br/>
  <b>Multi-Agent Autonomous World Engine</b>
</p>

<p align="center">
  <i>"The world doesn't change — the agent doesn't think."</i><br/>
  <i>"世界不变化，Agent 不思考。"</i>
</p>

---

## 🎯 Core Idea · 核心思想

```
Agent 维护四组 P 快照（上次感官锁存）。每 0.3s poll 一次 → 得到 Q（当前世界）。
P vs Q 出现差异 → KL 信号产生 → 触发 LLM 决策 → 做动作 → 回到观察基线。
```

**不是轮询。不是定时器。世界推动 agent，而不是 agent 推动世界。**

---

## 🏗 Architecture · 全景架构

```
                    ┌────────────── config/ ──────────────┐
                    │  world.yaml · prompts.yaml · llm.yaml │
                    │  All behavior in YAML. Zero hardcode. │
                    └──────────────────────────────────────┘

┌──── layers ────┐   ┌──── entity ────┐   ┌──── systems ───────────────┐
│                │   │                 │   │                            │
│  Visual        │   │  Entity:        │   │  SensorySystem             │
│   properties:  │   │   id name zone  │   │   · poll vision+hearing    │
│   {look,expr}  │   │   pos status    │   │   · hearing→memory retention│
│                │   │   layers: dict  │   │                            │
│  Auditory      │   │                 │   │  InteractionSystem         │
│   properties:  │   │  P/KL snaps:    │   │   · interact() sole entry  │
│   {speech}     │   │   auditory,     │   │   · fuzzy_match_action()   │
│                │   │   visual,       │   │   · check_observing()      │
│  Interaction   │   │   state,        │   │                            │
│   actions:dict │   │   stale         │   │  DecaySystem               │
│                │   │                 │   │   · drive × t              │
│                │   │  observing:     │   │                            │
│                │   │   target,       │   │                            │
│                │   │   since,        │   │                            │
│                │   │   timeout       │   │                            │
│                │   │                 │   │                            │
└────────────────┘   └─────────────────┘   └────────────────────────────┘

                    ┌────────── KL Gate ──────────────┐
                    │  auditory  │  visual  │  state   │  temporal   │
                    │     P→Q    │   P→Q    │  P→Q     │   P→Q        │
                    │     ↓     │    ↓     │   ↓      │    ↓          │
                    │    ε_a   OR   ε_v   OR  ε_s   OR   ε_t          │
                    │                  ↓                               │
                    │           total_KL ≠ ""                          │
                    │                  ↓                               │
                    │            trigger decide                        │
                    └──────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │        brain.decide()            │  ← ① LLM
                    │  { action, dialogue, visual,     │
                    │    internal, self_deltas,        │
                    │    expects_reply, patience }      │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │         interact()               │
                    │  ① A.auditory = dialogue         │
                    │  ② A.visual   = expression       │
                    │  ③ A.apply_deltas(self_deltas)    │
                    └───┬──────────────────┬──────────┘
                        │                  │
                   target.is_agent    target.is_item
                        │                  │
                   return (0 LLM)    +interact_narrative (1 LLM)
                        │
              A → observing (if expects_reply)
              B polls → hears → KL triggers → B.decide()
```

---

## 🧠 P/Q/KL — 核心机制

```
P = 上轮锁存的感官快照 (agent 对世界的内部预期)
Q = 本轮 poll 的感官输入 (世界的实际状态)
ε = |Q - P| 的阈值化差异 (prediction error)
```

| Channel | P (last latch) | Q (current poll) | Trigger | Output |
|---------|---------------|------------------|---------|--------|
| **Auditory** | speaker_ids | hearing dict | speech_ts changed or speaker left range | `"杰洛特 说话了"` |
| **Visual** | entity_ids + expressions | vision dict | entity enter/leave or expression changed | `"特莉丝 进入视野"` |
| **State** | drives snapshot | current drives | any drive crosses {30, 60, 80} | `"thirst 突破60"` |
| **Temporal** | last decision time | now | idle > 30s | `"太久没事做了"` |

```
KL_total = join_if_any([KL_a, KL_v, KL_s, KL_t])

KL_total = ""  → continue observing (sleep 0.3s)
KL_total ≠ ""  → trigger decide()
```

---

## 🔄 Agent Loop · Agent 循环

```
          ┌──────────────┐
          │   observing   │ ← baseline, no LLM
          └──────┬───────┘
                 │ sensory.poll + decay.tick (every 0.3s)
                 ▼
          ┌─────────────┐
          │  compute KL  │
          └──┬───────┬───┘
             │       │
         KL=""   KL≠""
             │       │
             ▼       ▼
         sleep    ┌──────────────┐
         0.3s     │ check        │
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
                  ┌─────────────┐
                  │  interact()  │
                  │  write layer │
                  │  apply deltas│
                  └──────┬──────┘
                         │
              ┌──────────┼──────────┐
              │                     │
         target.is_agent       target.is_item
              │                     │
              ▼                     ▼
         expects_reply?        +interact_narrative LLM
          yes → observing          +gate transfer
          no  → idle
```

---

## 🎮 interact() — 统一入口

```
interact(A, target, action_name, decision):

  ① A.auditory.properties["current_speech"] = decision.dialogue
        → B 下轮 poll 时读到 → sensory.hearing["geralt"]

  ② A.visual.properties["expression"] = decision.visual
        → B 下轮 poll 时看到 → sensory.vision["geralt"]

  ③ A.apply_deltas(decision.self_deltas)
        → thirst -28, mood +3, coins -5

  ④ if target.is_agent:
        return                           ← NPC→NPC: 0 extra LLM
                                            B answers via own decide()

  ⑤ if target.is_item:
        await interact_narrative_llm()   ← NPC→Item: +1 LLM
                                            watermarking + deltas + gate
```

| Scenario | LLM #1 | interact_narrative | Total |
|----------|:------:|:-----------------:|:-----:|
| Observing (no event) | 0 | 0 | **0** |
| Gate opens → NPC→NPC | 1 | 0 | **1** |
| Gate opens → NPC→Item | 1 | 1 | **2** |

(v3: 4 calls per NPC→NPC interaction. v4: 1.)

---

## 📐 Design Principles · 设计原则

| # | Principle | 一句话 |
|---|-----------|--------|
| 1 | **P/Q/KL Drive** | 世界不变化，Agent 不思考 |
| 2 | **Observing Baseline** | Agent 常态是 poll，不是 decide |
| 3 | **Single interact()** | 一入口。无 submit/resolver/projection chain |
| 4 | **Layer Architecture** | 每层一个接口。observer 自己 poll，不 push |
| 5 | **Agent Autonomy** | B 用自己的 personality/drives/memory 决定回应，无替身投影 |
| 6 | **Config as Behavior** | 全 YAML。Python 零硬编码 |
| 7 | **LLM On-Demand** | NPC→NPC: 1 call。NPC→Item: 2 calls。Max |

---

## 📂 Project Structure · 项目结构

```
AgentWorld_Async/
│
├── config/
│   ├── world.yaml            # Entities: description + actions.description
│   ├── prompts.yaml           # agent_decision + interact_narrative templates
│   └── llm.yaml               # LLM provider (DeepSeek / OpenAI)
│
├── src/
│   ├── layers/                # Layer definitions · 层定义
│   │   ├── visual.py          #   properties: {look, expression}
│   │   ├── auditory.py        #   properties: {current_speech}
│   │   ├── interaction.py     #   actions: dict[str, dict]
│   │   └── agent.py           #   drives + sensory + memory
│   │
│   ├── entity/
│   │   └── entity.py          # Single Entity: +KL snaps +observing fields
│   │
│   ├── systems/               # Cross-layer orchestration · 跨层编排
│   │   ├── interaction.py     #   interact() + 5 helpers + check_observing()
│   │   ├── sensory.py         #   poll vision+hearing, hearing→memory
│   │   └── decay.py           #   drive × t
│   │
│   ├── agent/                 # Agent mind · Agent 心智
│   │   ├── brain.py           #   decide() + extract_json()
│   │   ├── drives.py          #   DriveSystem
│   │   ├── memory.py          #   AgentMemory {ts, text}
│   │   └── sensory_memory.py  #   VisionRecord, HearingRecord
│   │
│   ├── core/                  # Engine core · 引擎核心
│   │   ├── world.py           #   World container + entity factory
│   │   ├── kl_divergence.py   #   P/Q computation (to be layered)
│   │   ├── lifecycle.py       #   EntityLifecycle: spawn/despawn/transfer
│   │   ├── spatial_grid.py    #   O(1) proximity queries
│   │   └── clock.py           #   Simulated clock
│   │
│   ├── llm/
│   │   └── client.py          # LLM client (timeout 120s)
│   │
│   └── prompt/
│       ├── assembler.py       # Slot-based prompt assembly
│       └── loader.py          # YAML config loader
│
├── test_e2e_concurrent.py     # E2E test: observing + KL + trace
├── main.py                    # API server entry
└── README.md
```

**Deleted**: `resolver.py` (LLM #2–#4 chain), `event_bus.py` (unused pub/sub).  
**Net**: 16 source files, ~1600 lines (-900 from v3).

---

## 🚀 Quick Start · 快速开始

```bash
pip install -r requirements.txt
cp config/llm.yaml.example config/llm.yaml   # set API key
python test_e2e_concurrent.py                # 8-agent concurrent test (60s)
```

---

## 🌍 World Config · 世界配置

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

| v3 | v4 |
|----|----|
| `resolve: rule/llm` | deleted |
| `rule: {effects: {thirst: -30}}` | deleted — LLM outputs `self_deltas` |
| `public_attrs / private_attrs` | deleted |
| `describe: "..."` | `description: "..."` + `actions.{name}.description: "..."` |

---

## 💬 Conversation Flow · 对话流

```
[0.0s] 杰洛特 observing
[0.3s] poll → KL="" → sleep

[2.0s] 兰伯特 decide → "不关你的事" → 兰伯特.auditory
[2.3s] 杰洛特 poll → KL_a="兰伯特 说话了" → trigger → decide
       → "他回了。追问。" → interact → observing(兰伯特, 5s)

[4.0s] 兰伯特 decide → "你别躲，我问认真的" → 兰伯特.auditory
[4.3s] 杰洛特 poll → hearing → "他回了" → observing end → decide
       → 对话自然推进，无时间裂缝
```

```
A.speak → A.auditory (writes own blackboard)
            ↓
B polls → hears A → B's own decide → B.auditory (writes back)
            ↓
A polls → hears B → A's next decide
```

---

## 📋 Update Log · 更新记录

| Version | Date | Milestone |
|---------|------|-----------|
| **v4** | May 2026 | P/Q/KL four-channel gate + observing baseline |
| | | `interact()` unified entry. Delete submit/resolver/event_bus. |
| | | LLM calls 4→1 (NPC→NPC). World config description-only. |
| | | Agent autonomy: B answers via own brain, no proxy projection. |
| | | Codebase -900 lines net. Delete 2 dead files. |
| v3 | Apr 2026 | Story-first pipeline + per-agent projection + verify |
| v2 | Mar 2026 | Multi-agent async: inbox messaging, hybrid busy-queue |
| v1 | Feb 2026 | Single-agent demo with graph-based world model |

---

## 📄 License · 许可证

MIT
