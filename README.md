<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v5-ff6b35?style=flat-square" alt="v5">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License">
</p>

<h1 align="center">
  🏠 AgentWorld Async<br/>
  <sub>异步多智能体自主世界引擎</sub>
</h1>

<p align="center">
  <b>P/Q/KL-Driven · Layer-Architected · LLM-Powered</b><br/>
  <b>P/Q/KL 驱动 · 分层架构 · LLM 赋能</b>
</p>

<p align="center">
  <i>"The world doesn't change — the agent doesn't think."</i><br/>
  <i>"世界不变化，Agent 不思考。"</i>
</p>

---

## 🆚 vs Similar Projects · 同类项目对比

| | Generative Agents<br/><sub>Park et al. 2023<br/>生成式智能体</sub> | CrewAI / AutoGen | **AgentWorld Async** |
|---|---|---|---|
| **Decision trigger**<br/>决策触发 | Fixed-interval reflection<br/>固定间隔反思 | Tool-calling pipeline<br/>工具调用流水线 | **P/Q/KL attention gate**<br/>**注意力门控** — event-driven 事件驱动 |
| **LLM calls / interaction**<br/>每次交互 LLM 调用 | 3+ (plan + reflect + act) | 1 per tool call | **1** (NPC→NPC) · **2** (NPC→Object) |
| **Agent-to-agent**<br/>Agent 间通信 | One-way observation<br/>单向观察 | Message-passing<br/>消息传递 | **Mutual observation** — A writes blackboard, B polls<br/>**双向观察** — A 写黑板，B 轮询 |
| **Personality**<br/>个性 | Prompt only<br/>仅 Prompt | Prompt only<br/>仅 Prompt | **LLM #1 output drives behavior** — no proxy projection<br/>**LLM 自主输出驱动** — 无替身投影 |
| **Config**<br/>配置 | Code + JSON | Python decorators | **Pure YAML** — description-only, zero code changes<br/>**纯 YAML** — 仅描述，零代码改动 |
| **Memory**<br/>记忆 | Reflection-based summary<br/>反思摘要 | Chat history<br/>对话历史 | **Full decision JSON** — agent remembers everything<br/>**完整决策 JSON** — agent 记住全部输出 |
| **Architecture**<br/>架构 | Monolithic agent loop<br/>单体循环 | Distributed agents<br/>分布式 | **Layer-based container** — visual/auditory/interaction<br/>**层容器** — 视觉/听觉/交互分层 |
| **World scale**<br/>世界规模 | 25 agents, 2 days | N/A | 3 zones, 23 entities — **zero-code switchable**<br/>**零代码换世界** |

---

## 💡 Key Innovations · 核心创新

| # | Innovation 创新点 | Why It Matters 为什么重要 |
|---|-----------|---------------------|
| 1 | **P/Q/KL Attention Gate**<br/>注意力门控 | 4-channel parallel diff (auditory/visual/state/temporal). Agent only calls LLM when world actually changes. 0.3s polling replaces fixed-interval loops.<br/>四通道并行 diff（听觉/视觉/状态/时差）。世界真正变化时才触发 LLM。 |
| 2 | **Write-Pending Lock**<br/>写后锁让 | After interacting, agent yields exactly one poll cycle. Disrupted conversations self-repair without fixed timers.<br/>交互后 Agent 让渡一个轮询周期。断裂对话自动修复，无需固定时钟。 |
| 3 | **Unified `interact()`**<br/>统一交互入口 | NPC→NPC and NPC→Item share one code path. B answers via its own `decide()` — no proxy projection engine.<br/>NPC→NPC 和 NPC→Item 共用一条路径。B 用自己的 decide() 回应——无替身投影引擎。 |
| 4 | **Layer Architecture**<br/>分层架构 | Visual/Auditory/Interaction layers independently defined. Observers poll — no EventBus, no push, no gossip protocol.<br/>视觉/听觉/交互层独立定义。观察者轮询——无事件总线、无推送、无 gossip 协议。 |
| 5 | **Config-as-Behavior**<br/>配置即行为 | Every string, threshold, currency key, and drive limit injected from YAML. Swap `world.yaml` = new world. Zero Python changes.<br/>所有文本、阈值、货币键、属性上下限从 YAML 注入。换 `world.yaml` = 换世界。 |
| 6 | **Full Decision Memory**<br/>全决策记忆 | Entire LLM #1 output (dialogue, visual, internal, self_deltas, story, expects_reply, patience) recorded as JSON. Agent remembers what it said, did, and felt.<br/>LLM #1 全部输出（对话、表情、内心、属性、故事、期待回复、耐心）以 JSON 存入记忆。 |
| 7 | **Observing Baseline**<br/>观察基线 | Default state is observation. Decisions are triggered by change — not by a timer. "The world pushes the agent, not the other way around."<br/>默认状态是观察。变化触发决策——不是定时器。"世界推动 Agent，而非 Agent 推动世界。" |
| 8 | **Generic Layer Observation**<br/>通用层观察 | All layers inherit `Layer.observe(d)` + `observable_radius`. Sensory polls all layers generically. New modal (action/emotion/...) = 0 code changes. Add `layers.action: {properties: {}}` in YAML.<br/>所有层继承 `observe(d)` + `observable_radius`。感官系统遍历全部层。新模态零代码——YAML 加 `layers.action: {}`。 |
| 9 | **Property Verification** / SQLite Persistence<br/>属性校验 / 持久化 | `@register` decorator-based validator chain catches negative coins, out-of-range drives before apply. Optional `--persist world.db` snapshots all agent states + interactions to SQLite.<br/>`@register` 装饰器校验链在 apply 前拦截非法 delta。可选 `--persist` 持久化到 SQLite。

---

## 🏗 Architecture · 架构

```
                    ┌────────────── config/ ──────────────┐
                    │ world.yaml · prompts.yaml · llm.yaml │
                    │ All behavior in YAML · 全部行为YAML配置 │
                    └──────────────────────────────────────┘

┌──── layers ────┐   ┌──── entity ──────────────────┐
│ Visual         │   │  Entity: id name zone pos    │
│  · see(d) →    │   │  layers: {visual, auditory,  │
│    look+detail │   │           interaction, agent} │
│                │   │  + P/Q KL snapshots          │
│ Auditory       │   │  + _write_pending lock       │
│  · hear(d) →   │   │  + observing state            │
│    speech+vol  │   └──────────────────────────────┘
│                │
│ Interaction    │   ┌──── KL Gate · 门控 ──────────┐
│  · actions:dict│   │  auditory │ visual │ state    │
│  · apply(d)    │   │    P→Q       P→Q     P→Q     │
└────────────────┘   │    ε_a   OR  ε_v  OR ε_s  OR ε_t│
                     │           ↓                   │
┌──── systems ────┐  │      total_KL ≠ ""            │
│ SensorySystem   │  │           ↓                   │
│  · poll vision  │  │      trigger decide           │
│  · poll hearing │  └───────────────────────────────┘
│  · hearing→mem  │                  │
│                 │  ┌───────────────┴───────────────┐
│ InteractionSys  │  │       brain.decide()  ← 1 LLM │
│  · interact()   │  │  { action, dialogue, visual,  │
│  · fuzzy_match  │  │    internal, self_deltas,     │
│  · check_observe│  │    expects_reply, patience }  │
│                 │  └───────────────┬───────────────┘
│ DecaySystem     │                  │
│  · drive × t    │  ┌───────────────┴───────────────┐
└─────────────────┘  │         interact()            │
                     │  ① A.auditory = dialogue      │
                     │  ② A.visual   = expression    │
                     │  ③ A.apply_deltas(self)       │
                     │  ④ memory.record(decision)     │
                     │  ⑤ _write_pending = True      │
                     └───┬──────────────┬────────────┘
                         │              │
                    target.is_agent  target.is_item
                         │              │
                   return (0 LLM)  +narrative LLM (1)
                         │
              A → observing (expects_reply)
              B polls → hears A → B.decide()
```

---

## 🧠 P/Q/KL Gate · 门控机制

```
P = 上轮锁存的感官快照 (agent 的内部预期 · internal prediction)
Q = 本轮 poll 的感官输入 (世界的实际状态 · the world as it is)
ε = |Q - P| 的阈值化差异 (prediction error · 预测误差)

┌──────────┬──────────────────┬──────────────────┬───────────────────────┐
│ Channel  │ P (last latch)   │ Q (current poll) │ Trigger condition      │
│ 通道     │ 上次锁存          │ 本轮轮询          │ 触发条件               │
├──────────┼──────────────────┼──────────────────┼───────────────────────┤
│ 🎧听觉   │ speaker_ids      │ hearing dict     │ speech_ts changed OR   │
│ Auditory │                  │                  │ speaker left range     │
│ 👁视觉   │ entity_ids       │ vision dict      │ entity enter/leave OR  │
│ Visual   │ + expressions    │                  │ expression changed     │
│ 💪状态   │ drives snapshot  │ current drives   │ any drive crosses      │
│ State    │                  │                  │ {30, 60, 80}           │
│ ⏰时差   │ last decide time │ now              │ idle > 30s             │
│ Temporal │                  │                  │                        │
└──────────┴──────────────────┴──────────────────┴───────────────────────┘

KL_total = join_if_any([KL_a, KL_v, KL_s, KL_t])
  ""   → continue observing · 继续观察 (sleep 0.3s)
  !="" → trigger decide() · 触发决策
```

---

##  🔄 Agent Loop · Agent 循环

```
          ┌──────────────┐
          │   observing   │ ← baseline, no LLM · 基线, 无 LLM
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
         继续观察  │ observing    │── replied/left/timeout → back to KL
                  │ (if expects  │   已回复/走远/超时 → 回到 KL
                  │  _reply)     │
                  └──────┬───────┘
                         │ resolved · 已解决
                         ▼
                  ┌─────────────┐
                  │  decide()    │ ← ① LLM
                  └──────┬──────┘
                         ▼
                  ┌──────────────┐
                  │  _write_     │── True → release + sleep poll
                  │  pending?    │   释放 → 让渡一个轮询周期
                  └──────┬───────┘
                         │ False
                         ▼
                  ┌─────────────┐
                  │  interact()  │
                  │  + observing │
                  └─────────────┘
```

---

## 🎮 interact() — Unified Entry · 统一入口

```
interact(A, target, action_name, decision)

  ① A.auditory["current_speech"] = decision.dialogue
        → B polls → sensory.hearing[A] · B 轮询听到

  ② A.visual["expression"] = decision.visual
        → B polls → sensory.vision[A] · B 轮询看到

  ③ A.apply_deltas(decision.self_deltas)
        → thirst -28, mood +3 · 口渴 -28, 心情 +3

  ④ agent.memory.record(json.dumps(decision))
        → full multimodal memory retention · 全模态记忆留存

  ⑤ A._write_pending = True
        → yield next poll cycle · 让渡下一轮询周期

  ⑥ if target.is_agent → return                    (NPC→NPC: 0 extra LLM)
     if target.is_item  → interact_narrative LLM    (NPC→Item: 1 extra LLM)
     if gate → world.transfer_zone()
```

| Scenario · 场景 | LLM calls · LLM 调用 |
|----------|:--------:|
| Observing (idle) · 观察中 | **0** |
| NPC→NPC conversation · 对话 | **1** |
| NPC→Item interaction · 物交互 | **2** |

---

## 📐 Design Principles · 设计原则

| # | Principle · 原则 | Summary · 概述 |
|---|-----------|---------|
| 1 | **P/Q/KL Driven** · 变化驱动 | World changes → agent decides. Not a timer. · 世界变化 → Agent 决策。不是定时器。 |
| 2 | **Observing Baseline** · 观察基线 | Default state is observation. Decisions are rare. · 默认状态是观察。决策是稀有事。 |
| 3 | **Single interact()** · 统一入口 | One entry point. No submit/resolver/projection chain. · 一个入口。无 submit/resolver 链。 |
| 4 | **Layer Architecture** · 分层架构 | Each layer exposes one method. Observers poll. · 每层暴露一个方法。观察者轮询。 |
| 5 | **Agent Autonomy** · Agent 自治 | B answers via own decide(). No proxy projection. · B 用自己的 decide()回应。无替身投影。 |
| 6 | **Config as Behavior** · 配置即行为 | All text/thresholds/currencies in YAML. Zero Python hardcode. · 全部 YAML。零 Python 硬编码。 |
| 7 | **LLM On-Demand** · 按需调用 | 1 call for NPC→NPC. 2 for NPC→Item. Maximum. · NPC→NPC 1 次。NPC→Item 2 次。极致。 |
| 8 | **Generic Layer Obs** · 通用层观察 | All layers inherit `observe(d)`. Sensory polls generically. New modal = YAML only. · 全层继承 `observe(d)`。感官通用轮询。新模态仅 YAML。 |
| 9 | **Verified Deltas** · 属性校验 | `@register` validator chain catches illegal deltas before apply. Coins never negative. · `@register` 校验链在 apply 前拦截非法属性变化。 |

---

## 📂 Structure · 项目结构

```
AgentWorld_Async/                # 24 source files · 24 个源文件 · ~2000 lines
├── config/
│   ├── world.yaml               # Entities + zones + simulation params
│   ├── prompts.yaml              # Templates + slots + text_labels
│   └── llm.yaml                  # LLM provider config
├── src/
│   ├── layers/                   # Layer definitions · 层定义 (5 files)
│   │   ├── visual.py             #   properties: {look, expression}
│   │   ├── auditory.py           #   properties: {current_speech}
│   │   ├── interaction.py        #   actions dict + apply_deltas
│   │   └── agent.py              #   drives + sensory + memory
│   ├── entity/                   # Entity model · 实体模型 (2 files)
│   │   └── entity.py             #   +KL snaps + observing + write-pending
│   ├── systems/                  # Cross-layer orchestration · 跨层编排 (3 files)
│   │   ├── sensory.py            #   poll vision+hearing, hearing→memory
│   │   ├── interaction.py        #   interact() + check_observing()
│   │   └── decay.py              #   drive × t
│   ├── agent/                    # Agent mind · Agent 心智 (5 files)
│   │   ├── brain.py              #   decide() + extract_json()
│   │   ├── drives.py             #   DriveSystem (currency-key-aware)
│   │   ├── memory.py             #   AgentMemory {ts, text}
│   │   └── sensory_memory.py     #   Vision/Hearing record + to_prompt
│   ├── core/                     # Engine core · 引擎核心 (5 files)
│   │   ├── world.py              #   World container + entity factory
│   │   ├── kl_divergence.py      #   4-channel P/Q KL with text injection
│   │   ├── lifecycle.py          #   EntityLifecycle
│   │   ├── spatial_grid.py       #   O(1) proximity queries
│   │   └── clock.py              #   Simulated clock
│   ├── llm/client.py             # LLM client (OpenAI / DeepSeek)
│   ├── prompt/                   # Prompt assembly · Prompt 组装 (2 files)
│   │   ├── assembler.py          #   Slot + condition rendering
│   │   └── loader.py             #   YAML config loader
│   └── loop.py                   # Agent loop (single run_agent())
├── main.py                       # Entry point · 入口
├── requirements.txt
└── README.md
```

---

##  🌍 World Config · 世界配置

```yaml
# No resolve. No rule. No effects. Only descriptions.
# 无 resolve。无 rule。无 effects。只有 description。
# LLM reads the description and decides what happens.
# LLM 阅读描述，自主决定交互结果。

- id: square_well
  name: 水井
  description: "广场中央的石砌水井。井水清澈冰凉。"
  interaction:
    actions:
      打水:
        description: "放下木桶，摇辘轳打水。井水来自地下暗河，常年清凉甘甜。"

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

## 🚀 Quick Start · 快速开始

```bash
pip install -r requirements.txt
cp config/llm.yaml.example config/llm.yaml   # 配置 API Key
python main.py                               # 8-agent concurrent test · 60s
python main.py --runtime 180 --validate      # 3min + validation · 验证模式
```

---

## 📋 Update Log · 更新记录

| Version | Date · 日期 | Milestone · 里程碑 |
|---------|------|-----------|
| **v5** | Jun 2026 | Generic Layer.observe() + observable_radius. Sensory polls all layers. Channel_kl full dict diff. Modal_layer_map from YAML. Property verification (@register). SQLite persistence (--persist). Pinned memory. 0-code new modal. · 通用层观察、全量 dict diff、属性校验、SQLite 持久化 |
| **v4** | May 2026 | P/Q/KL gate + observing baseline + write-pending lock · 门控 + 观察基线 |
| | | Unified interact(). Config decoupling. Full memory retention. · 统一入口、配置解耦 |
| | | Delete resolver/event_bus. LLM calls: 4→1. Net code: -24000 lines. · 删 resover/event_bus |
| v3 | Apr 2026 | Story-first pipeline + per-agent projection + verify |
| v2 | Mar 2026 | Multi-agent async: inbox messaging, hybrid busy-queue · 多 Agent 异步 |
| v1 | Feb 2026 | Single-agent demo with graph-based world model · 单 Agent 图模型 |

---

## 📄 License · 许可证

MIT
