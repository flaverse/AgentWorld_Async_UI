<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v6-ff6b35?style=flat-square" alt="v6">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License">
</p>

<h1 align="center">
  AgentWorld Async
</h1>

<p align="center">
  <b>P/Q/KL-Driven · Layer-Architected · Slot-Vector Prompting · 4-Phase Pipeline</b>
</p>

<p align="center">
  <i>The world doesn't change — the agent doesn't think.</i>
</p>

---

## System Architecture

```mermaid
flowchart TB
    subgraph Config["config/ (YAML)"]
        world_yaml["world.yaml"]
        prompt_yaml["prompts.yaml"]
    end

    subgraph World["World Container"]
        world_engine["entity factory"]
        spatial["spatial grid"]
        lifecycle["lifecycle"]
    end

    subgraph Layer["Entity Layers"]
        visual["Visual<br/>observe(d)"]
        auditory["Auditory<br/>observe(d)"]
        inter["Interaction<br/>hidden · gate"]
        agent["Agent<br/>p-channels · drives"]
    end

    subgraph Sensory["Sensory System"]
        poll["generic poll<br/>all entity.layers"]
    end

    subgraph AgentLoop["Agent Loop (4-phase)"]
        s["SENSE"]
        k["KL GATE"]
        d["DECIDE"]
        a["ACT"]
    end

    subgraph LLM["LLM Interface"]
        brain["Brain<br/>decide()"]
        narrative["Narrative<br/>resolve_npc_item()"]
        assembler["Slot Assembler<br/>vector dispatch"]
    end

    Config --> World
    World --> Layer
    Sensory --> Layer
    AgentLoop --> Sensory
    AgentLoop --> LLM
    LLM --> Config
    AgentLoop --> World
```

---

## Agent Loop — 4-Phase Pipeline

```mermaid
sequenceDiagram
    participant S as SensorySystem
    participant D as DecaySystem
    participant K as KL Gate
    participant B as Brain
    participant I as InteractionSystem

    loop 0.3s poll
        Note over S,D: PHASE 1 — SENSE
        S->>S: poll entity.layers
        D->>D: tick(elapsed)

        Note over K: PHASE 2 — KL GATE
        K->>K: total_kl(P, Q)
        alt KL empty
            S->>S: sleep · continue
        end

        Note over B: PHASE 3 — DECIDE
        B->>B: assemble(ctx, slot_vector)
        B->>B: LLM #1
        B-->>B: {action, dialogue, visual, ...}
        B->>B: write-pending check

        Note over I: PHASE 4 — ACT
        I->>I: interact(agent, target, decision)
        I->>I: write layers · apply deltas
        alt target is Item
            I->>B: LLM #2 (narrative)
        end
    end
```

---

## P/Q/KL Attention Gate

```mermaid
flowchart LR
    subgraph P["Previous State (P)"]
        p1["p_channels"]
        p2["p_state"]
        p3["p_stale"]
    end

    subgraph Q["Current Input (Q)"]
        q1["sensory.channels"]
        q2["drives.attrs"]
        q3["time.now()"]
    end

    subgraph Diff["KL Divergence"]
        d1["channel_kl<br/>entity enter/leave/change"]
        d2["state_kl<br/>threshold-cross detection"]
        d3["stale_kl<br/>idle timeout"]
    end

    p1 --> d1
    q1 --> d1
    p2 --> d2
    q2 --> d2
    p3 --> d3
    q3 --> d3

    d1 --> gate{"any trigger"}
    d2 --> gate
    d3 --> gate

    gate -->|"no change"| idle["sleep · observe"]
    gate -->|"changed"| act["trigger decide()"]
```

---

## Layer Model — Three Channels

```mermaid
flowchart TB
    subgraph Public["Public Channels (sensory-pollable)"]
        v["visual layer<br/>look · expression · detail"]
        aud["auditory layer<br/>current_speech · speech_ts"]
    end

    subgraph SemiPublic["Interaction Channel"]
        i_pub["properties.description<br/>visible at interaction range"]
    end

    subgraph Private["Interaction — Private"]
        i_priv["hidden{}<br/>taste · quality · secret<br/>(revealed only on interact)"]
        i_gate["gate<br/>(engine-only zone transfer)"]
    end

    subgraph Observer["Observer Agent"]
        sensory["SensorySystem.poll()"]
        prompt["LLM Decision Context"]
        interact["interact()"]
        narrative["Narrative LLM Context"]
    end

    v --> sensory
    aud --> sensory
    sensory --> prompt
    i_pub --> sensory
    i_pub --> prompt
    i_priv --> narrative
    i_gate --> interact
    interact --> narrative
```

---

## Slot Vector System

```mermaid
flowchart TB
    subgraph Definition["prompts.yaml — Slot Definitions"]
        s1["persona: {condition: name, template: ...}"]
        s2["kl_divergence: {condition: kl_text, template: ...}"]
        s3["recent_memory: {condition: memory_text, template: ...}"]
        s4["world_rules: {template: ...}"]
    end

    subgraph Template["Template — Slot Mask"]
        mask["agent_decision: [persona, world_rules, kl_divergence, recent_memory, ...]"]
    end

    subgraph Context["Runtime Context (ctx)"]
        ctx_keys["{name: Geralt, kl_text: '', memory_text: '...', ...}"]
    end

    subgraph Assemble["Assembler.assemble(template, ctx)"]
        loop["for name in mask:"]
        check{"ctx[slot.condition]<br/>is truthy?"}
        render["safe_format(slot.template, ctx)"]
        skip["skip"]
    end

    Definition --> Template
    Template --> loop
    Context --> check
    loop --> check
    check -->|yes| render
    check -->|no| skip
    render --> prompt["Rendered Prompt"]
```

---

## `interact()` — Unified Entry

```mermaid
flowchart TD
    interact["interact(agent, target, decision, world)"]

    write["write agent layers<br/>dialogue → auditory · visual → visual<br/>memory.record(decision)"]
    deltas["apply self_deltas<br/>+ verification clamp"]
    lock["write_pending = True"]

    branch{"target type"}
    npc["NPC → NPC<br/>return (0 LLM)"]
    item["NPC → Item<br/>narrative LLM (+1)"]
    gate["gate transfer<br/>if layer.gate exists"]

    result["return ActionResult"]

    interact --> write
    write --> deltas
    deltas --> lock
    lock --> branch
    branch -->|is_agent| npc
    branch -->|is_item| item
    item --> gate
    npc --> result
    gate --> result
```

---

## Comparison

| | Generative Agents<br/><sub>Park et al. 2023</sub> | CrewAI / AutoGen | **AgentWorld Async** |
|---|---|---|---|
| **Decision trigger** | Fixed-interval reflection | Tool-calling pipeline | **P/Q/KL gate** — event-driven |
| **LLM calls / interaction** | 3+ (plan + reflect + act) | 1 per tool call | **1** (NPC→NPC) · **2** (NPC→Item) |
| **Communication** | One-way observation | Message-passing | **Mutual observation** — write to layer, others poll |
| **Personality** | Prompt only | Prompt only | **Self-determined** — LLM output drives behavior |
| **Config** | Code + JSON | Python decorators | **Pure YAML** — zero code to switch worlds |
| **Memory** | Reflection summary | Chat history | **Full decision JSON** — all modalities |
| **Architecture** | Monolithic loop | Distributed agents | **Layer-based** — Entity/Layer clean separation |
| **Slot system** | Hardcoded | N/A | **Vector dispatch** — condition = ctx key |

---

## Key Innovations

| # | Innovation | Description |
|---|-----------|-------------|
| 1 | **P/Q/KL Attention Gate** | 4-channel parallel diff. Agent only calls LLM when world changes. No timers. |
| 2 | **4-Phase Pipeline** | SENSE → KL GATE → DECIDE → ACT. Each phase independently skipable. |
| 3 | **Slot Vector System** | All slots in one registry. Template = name list. `condition` = ctx key. Zero code to add a slot. |
| 4 | **Layer Architecture** | Visual/Auditory/Interaction layers. `observe(d)` is the sole interface. Polls are generic. |
| 5 | **Three Visibility Scopes** | Public (visual/auditory) → Semi-public (interaction description) → Private (hidden/gate). |
| 6 | **Natural Language Actions** | No action registry. LLM describes what it wants. Engine matches to entities. |
| 7 | **Memory-Driven Self-Regulation** | Full decision JSON in memory. LLM sees its own history, avoids repetition autonomously. |
| 8 | **Config-as-Behavior** | All text, thresholds, currencies from YAML. Zero hardcoded domain knowledge. |
| 9 | **AgentLayer Isolation** | All agent state (KL, drives, memory) on AgentLayer. Entity is pure container. |
| 10 | **Typed LoopConfig** | Dataclass replaces raw dict — type-safe, IDE-completable. |

---

## Project Structure

```
AgentWorld_Async/                  # 33 source files · ~1900 lines
├── config/
│   ├── world.yaml                 # 3 zones, 28 entities, simulation params
│   ├── prompts.yaml               # system_prompts, templates, slots, labels
│   └── llm.yaml                   # provider (OpenAI/DeepSeek/MiniMax), model
├── src/
│   ├── layers/                    # Layer definitions (5 files)
│   │   ├── base.py                #   Layer base: observable_radius, observe(d)
│   │   ├── visual.py              #   VisualLayer: visible_radius, sprite
│   │   ├── auditory.py            #   AuditoryLayer: audible_radius, speech
│   │   ├── interaction.py         #   InteractionLayer: hidden, gate, apply_deltas
│   │   └── agent.py               #   AgentLayer: p_channels, drives, write-pending
│   ├── entity/                    # Entity model (1 file)
│   │   └── entity.py              #   Entity: id, name, zone, pos, layers{}
│   ├── systems/                   # Cross-layer orchestration (3 files)
│   │   ├── sensory.py             #   Generic layer poll → sensory.channels
│   │   ├── interaction.py         #   interact() + find_entity_at + resolve_npc
│   │   └── decay.py               #   DriveSystem.tick(elapsed)
│   ├── agent/                     # Agent mind (5 files)
│   │   ├── brain.py               #   decide() + extract_json()
│   │   ├── drives.py              #   DriveSystem: attrs, decay, prompt table
│   │   ├── memory.py              #   AgentMemory: ring buffer, to_prompt_text
│   │   ├── sensory_memory.py      #   SensoryMemory: channels[ch][eid] → SensorRecord
│   │   └── inbox.py               #   Inbox: send / drain / to_prompt_text
│   ├── core/                      # Engine core (6 files)
│   │   ├── world.py               #   World container, entity factory, spatial grid
│   │   ├── kl_divergence.py       #   4-channel P/Q KL diff, state threshold
│   │   ├── verification.py        #   @register chain, attribute bounds check
│   │   ├── persistence.py         #   SQLite WorldDB (runs, snapshots, interactions)
│   │   ├── lifecycle.py           #   EntityLifecycle: spawn, transfer_zone
│   │   ├── spatial_grid.py        #   O(k) cell-based proximity queries
│   │   └── clock.py               #   Simulated clock, configurable timescale
│   ├── llm/                       # LLM client (1 file)
│   │   └── client.py              #   OpenAI/DeepSeek/MiniMax, retry, response_format
│   ├── prompt/                    # Prompt assembly (2 files)
│   │   ├── assembler.py           #   Slot vector dispatch + safe_format
│   │   └── loader.py              #   YAML config reader
│   └── loop.py                    #   4-phase pipeline + LoopConfig dataclass
├── main.py                        # CLI: --test, --demo, --persist, --validate
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
| **v6** | Slot vector system — condition = ctx key, zero-code slot addition. Duplication filter deleted (memory-driven self-regulation). Observing state machine deleted (KL gate is the wait mechanism). 4-phase pipeline (SENSE→KL→DECIDE→ACT). Dead code elimination: -364 lines, -3 files. Three visibility scopes for interaction layer. |
| v5.2 | Action dict eliminated. Hidden properties + gate on InteractionLayer. KL text injection. |
| v5 | Generic Layer.observe(). Sensory polls all layers. Property verification. SQLite persistence. |
| v4 | P/Q/KL gate + observing baseline + write-pending lock. Unified interact(). |
| v3 | Story-first pipeline + per-agent projection + verify |
| v2 | Multi-agent async: inbox messaging, hybrid busy-queue |
| v1 | Single-agent demo with graph-based world model |

---

## License

MIT
