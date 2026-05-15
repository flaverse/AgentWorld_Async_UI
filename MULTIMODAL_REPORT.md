# AgentWorld Async v5 — Multimodal Report

**Run**: 180s | 8 agents | 128 actions | 2026-05-15

---

## 1. Action Diversity & Duplication

| Agent | Actions | Unique | Repeats | Adjacent | Dup% |
|-------|---------|--------|---------|----------|------|
| 卓尔坦 | 14 | 14 | 0 | 0 | 0.0% |
| 特莉丝 | 15 | 15 | 0 | 0 | 0.0% |
| 兰伯特 | 17 | 16 | 1 | 0 | 5.9% |
| 叶奈法 | 16 | 15 | 1 | 1 | 6.2% |
| 丹德里恩 | 13 | 12 | 1 | 1 | 7.7% |
| 杰洛特 | 11 | 10 | 1 | 1 | 9.1% |
| 维瑟米尔 | 22 | 17 | 5 | 0 | 22.7% |
| 凯拉 | 20 | 15 | 5 | 1 | 25.0% |

**Overall**: 14/128 (10.9%) all-time repeats, only 4 (3.3%) adjacent. Duplication mute filter effectively prevents consecutive same-output spam. Repeat patterns are spaced (gap ≥2), caused by return to same scene after pursuing a different target in between — a scene-context issue, not a filter failure.

---

## 2. Output Modality Distribution

| Modality | Count | Coverage | Length |
|----------|-------|----------|--------|
| Story | 84 | 66% | avg 52 chars, range [23, 98] |
| Dialogue | 101 | 79% | avg 40 chars, range [8, 91] |
| Visual | 114 | 89% | — (expression/gesture) |
| Internal | 114 | 89% | — (inner monologue) |

**Narrative-target alignment**: 68/128 (53%) stories explicitly mention the interaction target.

All four modalities are well-populated. 89% visual + internal coverage means agents express nonverbal cues and inner thoughts nearly every action. Only 66% have story — stories are optional per the prompt schema and tend to be omitted for simple solo actions (walking, drinking alone).

---

## 3. Action Type Distribution

| Category | Count | % |
|----------|-------|---|
| drink/consume | 44 | 34% |
| talk_to_NPC | 41 | 32% |
| move/walk | 30 | 23% |
| bar_interact | 9 | 7% |
| other | 2 | 2% |
| rest | 1 | 1% |
| observe | 1 | 1% |

Social + drinking = 66% of all actions. This is natural for a tavern-centric world configuration. Move/walk (23%) covers travel between targets/positions. Low event diversity (1 rest, 1 observe, 0 gwent/combat/theft) is a world-design issue — the entity config defines what actions are available.

---

## 4. Social Fabric

NPC↔NPC: 41/128 (32%). Response rate: 38/41 (93%).

| Caller | → Target | Count |
|--------|----------|-------|
| 维瑟米尔 | → 杰洛特 | 10 |
| 兰伯特 | → 杰洛特 | 5 |
| 丹德里恩 | → 维瑟米尔 | 3 |
| 特莉丝 | → 卓尔坦 | 3 |
| 兰伯特 | → 维瑟米尔 | 2 |
| 凯拉 | → 叶奈法 | 2 |
| 卓尔坦 | → 特莉丝 | 2 |
| 卓尔坦 | → 丹德里恩 | 2 |
| 特莉丝 | → 兰伯特 | 2 |
| 特莉丝 | → 杰洛特 | 2 |
| 维瑟米尔 | → 特莉丝 | 2 |

**Social center**: 杰洛特 (6 inbound edges from 3 callers), 维瑟米尔 (4 inbound, 2 outbound). The rest forms a loose mesh.

**Zone mobility**: Only 2/8 agents (兰伯特, 特莉丝) crossed zones. 6 agents stayed rooted in their starting zone. Yennefer and Keira were stuck in herb_hut with only each other; the bar_zone crew formed a denser social cluster.

---

## 5. Thematic Scene Clusters (30s windows)

**0–30s** (23 acts, 8 agents): World startup. All agents converge on their initial targets — bar counter (12 hits), herb hut mortar (3). Low NPC↔NPC (2) — agents are still orienting.

**30–120s** (69 acts across 3 windows, 25 NPC↔NPC): Peak social activity. Jaskier joins Jaskier/Lambert/Vesemir at a table. Keira and Yennefer exchange 6 consecutive actions around the mortar. Vesemir tells stories, Jaskier listens, Lambert interjects.

**120–180s** (32 acts, 14 NPC↔NPC): Sustained conversation but thinning. Keira dominates the mortar (17 total actions on it). Vesemir continues as social hub. Jaskier's actions show "waiting for someone to speak" — observing state machine in effect.

**180–210s** (4 acts, 0 NPC↔NPC): Wind-down tail. Only 4 agents active, all solo actions (drink, check notice board).

---

## 6. Self-Delta Attribute Distribution

| Attribute | Count |
|-----------|-------|
| social | 80 |
| fun | 52 |
| thirst | 33 |
| energy | 18 |
| mood | 8 |
| hunger | 5 |
| coins | 3 |

Social and fun are the most-adjusted attributes — consistent with a tavern social scene. Verification flags were triggered during the run (thirst and social pushed below 0, fun above 100), but post-apply clamping kept values within [0,100] bounds. The flags indicate LLM doesn't see current attribute values in its decision prompt — a known issue (item #5 from the previous analysis, intentionally deferred).

---

## 7. Per-Agent Profile

### 丹德里恩 (13 acts, bar_zone)
Bard/observer role. 9/13 with dialogue. Top targets: bar counter (8), Vesemir (3). Opened by standing between Zoltan and Vesemir, patting both shoulders — performing the social connector role.

### 兰伯特 (17 acts, bar_zone→square)
Wolf school witcher, blunt personality. 13/17 with dialogue. Top targets: bar (5), Geralt (5), Vesemir (2). Crossed to square to drink from water well — showed independent exploration.

### 凯拉 (20 acts, herb_hut)
Alchemist. 16/20 with dialogue. 17 actions on the mortar — extreme fixation. Only 2 NPC↔NPC (both with Yennefer). Locked in herb_hut with no exit path.

### 卓尔坦 (14 acts, bar_zone)
Dwarf merchant. 14/14 with dialogue — never silent. 100% story coverage. Top targets: bar (7), ale (3), Triss (2). Talked about "business opportunities" — stayed in character.

### 叶奈法 (16 acts, herb_hut)
Sorceress. 16/16 with story — most narrative-heavy agent. 13 actions on mortar. Only 1 NPC↔NPC (with Keira). Also locked in herb_hut.

### 杰洛特 (11 acts, bar_zone)
Main character but low action count. 9/11 with dialogue. Top targets: bar (6), ale (3). Social center — received 5 inbound interactions, most of any agent.

### 特莉丝 (15 acts, bar_zone→square)
Sorceress, sociable. 12/15 with dialogue. Crossed zones. Top targets: bar (5), Zoltan (3), Lambert (2). Proposed going to a tavern together — initiated multi-agent activity.

### 维瑟米尔 (22 acts, bar_zone)
Highest action count. 18/22 with dialogue. 10 directed at Geralt — grandfather figure. Top targets: Geralt (10), bar (5), notice board (2). Social hub — told stories, drew a crowd.

---

## 8. Scorecard

| Dimension | Rating | Detail |
|-----------|--------|--------|
| **Action diversity** | ⚠️ FAIR | 10.9% repeat rate. Keira/Vesemir at 25%/23% — same-target fixation inflates repeats when only 1-2 meaningful targets exist in zone. |
| **Modality richness** | ✅ GOOD | 4/4 modalities active. 89% visual + internal, 79% dialogue. Stories at 66% — optional by design. |
| **Social fabric** | ✅ GOOD | 41 NPC↔NPC exchanges, 93% response rate, clear social center (Geralt), coherent grouping (bar table vs herb hut). |
| **Topic continuity** | ⚠️ FAIR | Strong within zones (bar crew talks, herb hut shares alchemy). Weak across zones — only 2 agents crossed, herb_hut pair isolated. |
| **Self-delta sanity** | ⚠️ FAIR | Clamping prevents negative values but LLM doesn't see current state. 33 thirst deltas on ~0-value thirst → mostly wasted prompts. |
| **Architecture** | ✅ GOOD | Phase pipeline clean, Entity/AgentLayer separation correct, typed LoopConfig, inbox drain timing fixed. |

---

## 9. Known Issues

1. **Keira + Yennefer locked in herb_hut**: herb_hut zone has only mortar + herbs as interact targets, no gate to bar_zone. Both agents loop on mortar actions. Fix: add a gate entity in herb_hut.
2. **Self-deltas uninformed**: LLM decision prompt lacks current attribute values. 33 thirst-consuming actions when thirst is already 0. Fix: inject `private_attrs` snapshot into decision prompt.
3. **Duplicate mute only compares to single previous**: Spaced repeats (gap ≥2) pass through. Fix: expand mute window to N=3 or use n-gram history.
