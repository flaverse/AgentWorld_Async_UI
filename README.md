<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/async-asyncio-purple?style=flat-square" alt="Async">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20MiniMax-green?style=flat-square" alt="LLM">
  <img src="https://img.shields.io/badge/architecture-v12-ff6b35?style=flat-square" alt="v12">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="License">
</p>

<h1 align="center">AgentWorld Async</h1>

<p align="center">
  <b>引擎提供事实。LLM 提供认知。<br/>
  世界不变，Agent 不动。</b>
</p>

---

## 架构总览

```
                         AgentWorld Async
══════════════════════════════════════════════════════════════════════════

  Config Layer                    Engine Layer                  LLM Layer
  ════════════                    ════════════                  ═════════

  slot_groups.yaml                ┌─────────────┐
  ┌──────────────────┐            │    World     │
  │ contract: [1,1]   │            │  ┌─────────┐ │
  │ world:   [1,1,1,1]│──────────▶│  │  Entity  │ │   ┌──────────────┐
  │ npc:     [1,1,1…] │            │  │ ┌─────┐ │ │   │  loop.py     │
  └──────────────────┘            │  │ │Layer│ │ │   │  4-phase     │
                                  │  │ └─────┘ │ │   │              │
  prompts.yaml                    │  └─────────┘ │   │ SENSE ─┐     │
  ┌──────────────────┐            │       │       │   │ GATE   │     │    ┌──────────┐
  │ 14 slots         │            │  AgentLayer  │   │ DECIDE │     │    │   LLM    │
  │ 6 traits         │            │ ┌──────────┐ │   │ ACT    │     │───▶│ DeepSeek │
  │ 3 sensory ch     │───────────▶│ │slot_mask │─┼──▶│        │     │    │          │
  │ output schemas   │            │ │  traits  │ │   │assembler│    │    │assembler │
  └──────────────────┘            │ │  drives  │ │   │.assemble│───▶│    │.assemble │
                                  │ │ sensory  │ │   │ (ctx,   │    │    │(ctx,mask)│
  world_friends.yaml              │ │  memory  │ │   │  mask)  │    │    └──────────┘
  ┌──────────────────┐            │ │  intent  │ │   └──────────┘    │
  │ world-group:full │            │ │          │ │    ↑         ↓    │
  │ npc-group: per   │───────────▶│ └──────────┘ │    │    interaction│
  │ traits: per      │            └─────────────┘    │    .interact  │
  │ zones, entities  │                  ↑            │    .narrative │
  └──────────────────┘            sensory.update()───┘              │
                                  (poll entities)                   │
                                                              ┌─────┴──────┐
  3 layers × 3 slots groups =   contract · world · npc       │   World    │
  per-agent mask = 0/1 toggle                                │  mutations │
  per-agent traits = tendency templates                      └────────────┘
```

---

## 五个核心思想

### 1. 引擎报告，LLM 判断

引擎不教 agent 怎么做。引擎只报告事实：`mood=5`、gate 存在、`target_name` 匹配成功。不说"心情很差"、不说"应该穿越"、不说"你可能想找这个实体"。全部认知判断权在 LLM，通过 YAML slot 组合引导。

### 2. 声明式认知架构（14 Slot，3 层）

Generative Agents 的 730 行认知代码 → 14 个 YAML slot + 45 行字符串格式化引擎。三层：
- **Contract** — 输出契约（`action_scope`、`output_contract`）
- **World** — 环境事实（`delta_gate`、`spatial`、`sensory`、`gate_highlight`）
- **NPC** — 角色驱动（`persona`、`main_thread`、`drive_values/context`、`memory`、`conversation`、`traits`、`intent_context`）

`slot_groups.yaml` 二维矩阵控制 per-agent slot 激活。新认知能力 = 加一行 YAML。零 Python 改动。

### 3. P/Q Delta Gate — 世界不变，Agent 不动

Agent 维护内部世界模型 P，每帧对比感官输入 Q。P=Q → 零 LLM 调用。P≠Q → 触发决策。四通道并行 diff（视觉·听觉·状态·时差）。发呆不花钱。

### 4. Per-Agent Traits + 战术意图反馈

行为倾向是声明式 trait 模板——`persistent`（坚持）、`novelty_seeking`（喜新）、`conversational_patience`（对话耐心）等——通过 YAML 矩阵 per-agent 分配。引擎追踪上轮意图、重复次数、对话不对称性，只报告事实。Ross 看到"第 8 轮追 Rachel"后，由他自己的 `persistent` trait 决定继续还是收手。消融实验 = 改一行 YAML。

### 5. 世界观即配置

换世界 = 换 YAML 文件。同一引擎驱动猎魔人酒馆、老友记咖啡厅、蜘蛛侠纽约。属性名相同 → prompts.yaml 一字不改。Gateway REST/WebSocket 接口——外部 agent 通过 `join/ perceive/act` 与自主 agent 共享同一决策通道。

---

## vs. Generative Agents

```
Generative Agents (~730 行认知 Python)        AgentWorld Async (~50 行 YAML)
══════════════════════════════════════        ═══════════════════════════════
  retrieve(memory) ───── importance score ─┐  main_thread:  "你的目标。更新它。"
  reflect(events)  ───── 3 LLM calls       │  persona:      "你是{name}。{personality}"
  plan(goal) ────────── plan tree struct   │  drive_values:  hunger=85 thirst=60...
                                            │  drive_context: 0=完全不饿 100=体力不支
  Sensory ─── location tree ──── visual    ├─ sensory_section: {视觉·听觉·可交互}
  Dialogue ── fixed format ───── template  │  recent_memory:  [经历]
                                            │  conversation:   [对话]
  Personality ── hardcoded in prompt       │  behavioral_traits: {trait 模板}
                                            │  intent_context:  {上轮回顾}
                                            │
  全部 Python 实现                           全部 YAML 声明
```

---

## 快速开始

```bash
pip install -r requirements.txt

python main.py --validate-config                  # 配置校验
python main.py --demo --world config/world_friends.yaml  # 单 Agent 演示
python main.py --runtime 180 --validate           # 3min 测试 + 属性校验
python main.py --output trace.json                # 保存 trace
python main.py --eval-report trace.json           # 18 指标评估报告
python main.py --api-port 8765                    # Gateway API

# 多世界热切换
python main.py --world config/world_friends.yaml
python main.py --world config/world_spiderman.yaml
```

---

## 实证

| 指标 | 7 Agent 180s (Friends, v12) |
|------|---------------------------|
| 总行动 | **206** |
| 对话率 | **99%** (204/206) |
| 线程完成率 | **53%** (16/30) |
| 区域跨越 | **14 次** (6 agents) |
| NPC↔NPC | **89%** |
| 心情改善 | **7/7** (+17.7) |
| 0% null | 全程无空转 |

---

## 版本

| Ver | 里程碑 |
|-----|--------|
| **v12** | 三层 slot 组 · slot_groups 矩阵 · per-agent traits · intent_context · drive 分拆 · token -67% |
| **v11** | target_name 精确匹配 · Director Phase 0 · Gateway API · 18 指标评估 |
| **v10** | 多世界热切换 · 哲学清理 · error_collector |
| **v9** | update_entity() 盲赋值 · target_changes · SessionManager |
| **v8** | Per-attr drive · Gate crossing |
| **v7** | 三通道感官 · P/Q dict copy fix |
| **v6** | Slot vector · -364 行死代码 |
| **v5** | 泛型 Layer.observe() · 校验 |
| **v4** | P/Q delta gate + write lock |

---

## License

MIT
