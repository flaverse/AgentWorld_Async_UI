<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v5-ff6b35?style=flat-square" alt="v5">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License">
</p>

<h1 align="center">
  AgentWorld Async<br/>
  <sub>异步多智能体自主世界引擎</sub>
</h1>

<p align="center">
  <b>P/Q/KL-Driven · Layer-Architected · Phase-Pipelined · LLM-Powered</b><br/>
  <b>P/Q/KL 驱动 · 分层架构 · 相位流水线 · LLM 赋能</b>
</p>

<p align="center">
  <i>"The world doesn't change — the agent doesn't think."</i><br/>
  <i>"世界不变化，Agent 不思考。"</i>
</p>

---

## Architecture

```mermaid
flowchart TB
    subgraph Config["config/ — YAML (0 Python hardcode)"]
        world["world.yaml<br/>entities · zones · simulation"]
        prompts["prompts.yaml<br/>templates · slots · labels"]
        llm_cfg["llm.yaml<br/>provider · model · key"]
    end

    subgraph Core["src/core/ — Engine"]
        world_engine["World<br/>entity factory · spatial grid · lifecycle"]
        kl["KL Divergence<br/>4-channel P/Q diff · state threshold · stale"]
        dup["Duplication<br/>@register chain · per-channel mute"]
        verify["Verification<br/>@register chain · bounds check"]
    end

    subgraph Layers["src/layers/ — Layer Definitions"]
        visual["VisualLayer<br/>observable_radius · expression"]
        auditory["AuditoryLayer<br/>observable_radius · current_speech"]
        interaction["InteractionLayer<br/>actions dict · apply_deltas"]
        agent_layer["AgentLayer<br/>KL snapshots · observing · write-lock"]
    end

    subgraph Entity["src/entity/ — Entity"]
        entity["Entity<br/>id · name · zone · pos · layers{}<br/>has() / get() / move_to()"]
    end

    subgraph Systems["src/systems/ — Cross-Layer Orchestration"]
        sensory["SensorySystem<br/>generic layer poll · channels dict"]
        interact_sys["InteractionSystem<br/>interact() · check_observing() · gate"]
        decay["DecaySystem<br/>drive × elapsed"]
    end

    subgraph Agent["src/agent/ — Agent Mind"]
        brain["Brain<br/>decide() → LLM #1"]
        memory["AgentMemory<br/>ring buffer · pinned entries"]
        drives["DriveSystem<br/>attr decay · prompt table"]
        sensory_mem["SensoryMemory<br/>channels[ch][eid] → SensorRecord"]
    end

    subgraph Loop["src/loop.py — Phase Pipeline"]
        loop["run_agent()<br/>SENSE → OBSERVE → KL → DECIDE → ACT<br/>LoopConfig dataclass"]
    end

    Entity --> Layers
    Systems --> Layers
    Systems --> Entity
    Systems --> Core
    Loop --> Systems
    Loop --> Core
    Loop --> Agent
    Agent --> Config
    Systems --> Config
    Core --> Config
```

---

## Agent Loop — Phase Pipeline

```mermaid
sequenceDiagram
    participant W as World
    participant S as SensorySystem
    participant D as DecaySystem
    participant K as KL Gate
    participant B as Brain (LLM-1)
    participant I as InteractionSystem

    loop every poll_interval (0.3s)
        Note over W,D: PHASE 1 — SENSE
        D->>W: tick(elapsed)
        S->>W: poll all entity.layers
        W-->>S: sensory.channels per agent

        Note over W,K: PHASE 2 — OBSERVING
        alt expects_reply
            I->>W: check_observing()
            alt replied / left / timeout
                W-->>W: continue (skip cycle)
            end
        end

        Note over K: PHASE 3 — KL GATE
        K->>W: total_kl(P_channels, Q_channels)
        alt KL = ""
            W-->>W: sleep poll_interval · continue
        end

        Note over B: PHASE 4 — DECIDE
        W->>W: drain inbox (only now)
        W->>B: decide(context)
        B-->>W: {action, dialogue, visual, internal, ...}
        W->>W: duplication check (mute repeats)

        Note over I: PHASE 5 — ACT
        W->>I: interact(agent, target, action, decision)
        I->>W: write agent layers (observable by others)
        I->>W: apply self_deltas · gate transfer
        alt NPC→Item
            I->>B: interact_narrative LLM (1 call)
        end
    end
```

---

## P/Q/KL Attention Gate

```mermaid
flowchart LR
    subgraph P["Previous (P)"]
        p_aud["p_channels[auditory]"]
        p_vis["p_channels[visual]"]
        p_state["p_state[drives]"]
        p_time["p_stale"]
    end

    subgraph Q["Current (Q)"]
        q_aud["sensory.channels[auditory]"]
        q_vis["sensory.channels[visual]"]
        q_state["current drives"]
        q_time["time.now()"]
    end

    subgraph Gate["KL Gate — 4-channel parallel diff"]
        k_aud["channel_kl(auditory)<br/>entity enter/leave/change"]
        k_vis["channel_kl(visual)<br/>entity enter/leave/change"]
        k_sta["state_kl<br/>threshold cross {30,60,80}"]
        k_tim["stale_kl<br/>idle > 30s"]
    end

    p_aud --> k_aud
    q_aud --> k_aud
    p_vis --> k_vis
    q_vis --> k_vis
    p_state --> k_sta
    q_state --> k_sta
    p_time --> k_tim
    q_time --> k_tim

    k_aud --> join{"join_if_any()"}
    k_vis --> join
    k_sta --> join
    k_tim --> join

    join -->|KL empty| sleep["sleep 0.3s<br/>continue observing"]
    join -->|KL triggered| trigger["trigger decide()"]
```

---

## Layer Architecture

```mermaid
classDiagram
    class Layer {
        <<abstract>>
        +observable_radius
        +properties dict
        +observe(d) dict
    }

    class VisualLayer {
        +visible_radius
        +sprite
        +sprite_sheet
        +observe(d) → {look, detail, expression}
    }

    class AuditoryLayer {
        +audible_radius
        +current_speech
        +speech_ts
        +observe(d) → {sound, volume, current_speech}
    }

    class InteractionLayer {
        +interaction_radius
        +public_attrs dict
        +private_attrs dict
        +actions dict
        +apply_deltas(d) dict
    }

    class AgentLayer {
        +autonomous · speed · radii
        +drives · sensory · memory · inbox
        +p_channels · p_state · p_stale
        +_write_pending
        +expects_reply · observing_target
    }

    class Entity {
        +id · name · zone · pos
        +layers dict
        +describe
        +has(layer) · get(layer)
        +move_to() · distance_to()
    }

    Layer <|-- VisualLayer
    Layer <|-- AuditoryLayer
    Layer <|-- InteractionLayer
    Layer <|-- AgentLayer
    Entity o-- Layer : layers{}

    class SensorySystem {
        +update(observer, entities)
        iterate entity.layers → call observe(d)
    }

    SensorySystem --> Layer : polls
```

---

## `interact()` — Unified Entry

```mermaid
flowchart TD
    interact["interact(agent, target, action, decision)"]
    validate{"action exists<br/>on target?"}
    error["return None"]
    write_layers["① _write_agent_layers()<br/>dialogue → auditory<br/>visual → visual<br/>memory.record(json(decision))"]
    apply_d["② _apply_deltas(self_deltas)<br/>+ verification"]
    lock["③ agent_layer._write_pending = True"]
    branch{"target type?"}
    npc_done["④ NPC→NPC<br/>return ActionResult<br/>(0 extra LLM)"]
    npc_item["④ _resolve_npc_item()<br/>interact_narrative LLM<br/>(+1 LLM call)"]
    gate["⑤ _handle_gate_transfer()<br/>zone teleport"]
    result["return ActionResult"]

    interact --> validate
    validate -->|no| error
    validate -->|yes| write_layers
    write_layers --> apply_d
    apply_d --> lock
    lock --> branch
    branch -->|target.is_agent| npc_done
    branch -->|target.is_item| npc_item
    npc_item --> gate
    npc_done --> result
    gate --> result
```

---

## Comparison

| | Generative Agents<br/><sub>Park et al. 2023</sub> | CrewAI / AutoGen | **AgentWorld Async** |
|---|---|---|---|
| **Decision trigger** | Fixed-interval reflection | Tool-calling pipeline | **P/Q/KL attention gate** — event-driven |
| **LLM calls / interaction** | 3+ (plan + reflect + act) | 1 per tool call | **1** (NPC→NPC) · **2** (NPC→Item) |
| **Agent-to-agent** | One-way observation | Message-passing | **Mutual observation** — A writes blackboard, B polls |
| **Personality** | Prompt only | Prompt only | **LLM #1 output drives behavior** — no proxy projection |
| **Config** | Code + JSON | Python decorators | **Pure YAML** — zero code changes to switch worlds |
| **Memory** | Reflection-based summary | Chat history | **Full decision JSON** — all modalities retained |
| **Architecture** | Monolithic agent loop | Distributed agents | **Layer-based** — Entity/AgenLayer separation |
| **State ownership** | Entity stores all | Agent stores all | **AgentLayer** only — Entity is universal container |

---

## Key Innovations

| # | Innovation | Why It Matters |
|---|-----------|----------------|
| 1 | **P/Q/KL Attention Gate** | 4-channel parallel diff (auditory/visual/state/temporal). Agent only calls LLM when world actually changes. Not a timer. |
| 2 | **Phase Pipeline** | SENSE → OBSERVING → KL GATE → DECIDE → ACT. Each phase can `continue` independently. Readable control flow. |
| 3 | **Unified `interact()`** | NPC→NPC and NPC→Item share one code path. B answers via own `decide()` — no proxy projection engine. |
| 4 | **Layer Architecture** | Visual/Auditory/Interaction layers. `observe(d)` is the sole interface. Sensory polls generically. New modal = YAML only. |
| 5 | **AgentLayer State Isolation** | All agent-specific state (KL snapshots, observing, write-lock, duplication) lives on AgentLayer. Entity is pure: id/name/zone/pos/layers. |
| 6 | **Config-as-Behavior** | All text, thresholds, currency keys from YAML. Swap `world.yaml` = new world. Zero Python changes. |
| 7 | **Full Decision Memory** | Entire LLM #1 output (dialogue, visual, internal, self_deltas, story, expects_reply, patience) recorded as JSON. |
| 8 | **Generic Layer Observation** | All layers inherit `observe(d)` + `observable_radius`. Sensory polls all layers generically. No hardcoded channel names. |
| 9 | **Typed LoopConfig** | Dataclass replaces raw dict — type-safe, IDE-completable, self-documenting. No more `cfg.get("what_was_that_key")`. |
| 10 | **Duplication Check** | `@register` validator chain. Per-channel mute mask from YAML. Sliding reference — only advances on genuinely new output. |

---

## Project Structure

```
AgentWorld_Async/                  # 36 source files · ~2300 lines
├── config/
│   ├── world.yaml                 # 3 zones, 28 entities, simulation params
│   ├── prompts.yaml               # system_prompts, templates, slots, labels, duplication
│   └── llm.yaml                   # provider (OpenAI/DeepSeek/MiniMax), model, key
├── src/
│   ├── layers/                    # Layer definitions (4 files)
│   │   ├── base.py                #   Layer base: observable_radius, observe(d)
│   │   ├── visual.py              #   VisualLayer: visible_radius, expression
│   │   ├── auditory.py            #   AuditoryLayer: audible_radius, current_speech
│   │   ├── interaction.py         #   InteractionLayer: actions dict, apply_deltas
│   │   └── agent.py               #   AgentLayer: KL snapshots, observing, write-lock
│   ├── entity/                    # Entity model (2 files)
│   │   ├── entity.py              #   Entity: id, name, zone, pos, layers{}, has/get
│   │   └── event_entity.py        #   EventEntity: spawned_at, lifespan, auto-expiry
│   ├── systems/                   # Cross-layer orchestration (3 files)
│   │   ├── sensory.py             #   Generic layer poll → sensory.channels
│   │   ├── interaction.py         #   interact() + check_observing() + find_entity_at
│   │   └── decay.py               #   DriveSystem.tick(elapsed)
│   ├── agent/                     # Agent mind (5 files)
│   │   ├── brain.py               #   decide() + extract_json()
│   │   ├── drives.py              #   DriveSystem: attrs dict, decay rates, prompt table
│   │   ├── memory.py              #   AgentMemory: ring buffer, pinned entries
│   │   ├── sensory_memory.py      #   SensoryMemory: channels[ch][eid] → SensorRecord
│   │   └── inbox.py               #   Inbox: send/drain/to_prompt_text
│   ├── core/                      # Engine core (7 files)
│   │   ├── world.py               #   World container, entity factory, spatial grid
│   │   ├── kl_divergence.py       #   4-channel P/Q KL diff, state threshold, stale
│   │   ├── duplication.py         #   @register chain, per-channel mute
│   │   ├── verification.py        #   @register chain, attribute bounds check
│   │   ├── persistence.py         #   SQLite WorldDB (runs, snapshots, interactions)
│   │   ├── lifecycle.py           #   EntityLifecycle: spawn/despawn/transfer
│   │   ├── spatial_grid.py        #   O(k) cell-based proximity queries
│   │   └── clock.py               #   Simulated clock, configurable timescale
│   ├── llm/                       # LLM client (1 file)
│   │   └── client.py              #   OpenAI/DeepSeek/MiniMax, retry, response_format
│   ├── prompt/                    # Prompt assembly (2 files)
│   │   ├── assembler.py           #   Slot assembly: content/runtime/topology providers
│   │   └── loader.py              #   YAML config reader
│   └── loop.py                    #   Phase pipeline + LoopConfig dataclass
├── main.py                        # CLI entry: --test, --demo, --persist, --validate
├── requirements.txt
└── README.md
```

---

## Quick Start

```bash
pip install -r requirements.txt
# Edit config/llm.yaml with your API key
python main.py                              # 8-agent concurrent test (default 60s)
python main.py --runtime 180 --validate     # 3min + attribute validation
python main.py --demo                       # Single-agent demo
python main.py --persist world.db           # Enable SQLite persistence
python main.py --output trace.json          # Save trace data
```

---

## Update Log

| Version | Milestone |
|---------|-----------|
| **v5.1** | Phase pipeline (SENSE→OBSERVING→KL→DECIDE→ACT). AgentLayer state isolation — all 11 agent-specific fields removed from Entity. Typed LoopConfig dataclass. Inbox drain timing fix. InteractionSystem method extraction (_write_agent_layers, _resolve_npc_item, _handle_gate_transfer). |
| **v5** | Generic Layer.observe() + observable_radius. Sensory polls all layers. channel_kl full dict diff. Property verification (@register). SQLite persistence (--persist). Dead code elimination (-24000 lines). |
| **v4** | P/Q/KL gate + observing baseline + write-pending lock. Unified interact(). Config decoupling. Full memory retention. |
| v3 | Story-first pipeline + per-agent projection + verify |
| v2 | Multi-agent async: inbox messaging, hybrid busy-queue |
| v1 | Single-agent demo with graph-based world model |

---

## License

MIT
