<p align="center">
  <img src="https://img.shields.io/badge/philosophy-删除胜过添加-ff6b35?style=flat-square" alt="Philosophy">
  <img src="https://img.shields.io/badge/architecture-Slot%20Vector-blue?style=flat-square" alt="SlotVector">
  <img src="https://img.shields.io/badge/engine-0%20认知代码-green?style=flat-square" alt="ZeroCognition">
</p>

# AgentWorld Async — Design Philosophy

## 核心命题

> **引擎提供世界，LLM 提供认知。**
>
> 引擎负责物理模拟：谁在哪里、能看见谁、距离多远、世界变没变。
> LLM 负责所有认知判断：什么是重要的、该做什么、不该重复什么、目标要不要换。
> **Python 代码不越过这条线。**

---

## 0. 和我们对比的基准：Generative Agents 的认知堆栈

Park et al. (2023) 的 Generative Agents 论文定义了四个核心认知阶段，每个都有独立的 Python 模块：

| GA 机制 | 实现方式 | 代码量 |
|---------|---------|--------|
| **记忆检索 (retrieve)** | Python 实现 `recency × importance × relevance` 加权 | ~200 行 |
| **重要度评估 (importance)** | Python 调 LLM 取 1-10 分 → 存入向量数据库 | ~80 行 |
| **反思 (reflect)** | 独立 LLM 调用时机 + 独立 prompt 路径 | ~150 行 |
| **计划 (plan)** | 独立 plan prompt + 计划树 (plan tree) 数据结构 | ~200 行 |

**合计 ~730 行 Python 代码。** 这些代码不生产世界内容——它们纯粹管理 LLM 的思维流程：什么时候该想、该想什么、该怎么评估记忆、该怎么把计划拆成子任务。

**AgentWorld Async: 45 行声明式调度引擎。所有"怎么思考"的决策权在 YAML 里——Python 从不涉及 hunger、dialogue 等任何领域语义。**

---

## 1. Slot 向量：认知即 YAML，非代码

### 1.1 核心洞察

> **认知模块不是独立的代码系统。认知模块是可组合的 prompt 片段。**

GA 把"反思"当独立代码路径——有独立的 LLM 调用、独立的 trigger、独立的存储。但本质上，"反思"只是一段告诉 LLM 怎么审视自己记忆的 prompt 文本。

如果 prompt 文本能解决问题，为什么需要一个独立的 Python 模块？

### 1.2 Assembler — 45 行，认知系统的唯一代码入口

```python
# 全引擎唯一处理"认知"的代码
def assemble(self, template_name, ctx):
    for name in template["slots"]:        # 模板定义了"要哪些 slot"
        slot = all_slots[name]            # 全局 registry 取定义
        cond = slot.get("condition", "")   # 开关条件
        if cond and not bool(ctx.get(cond)):
            continue                      # ctx 不满足 → 跳过
        parts.append(safe_format(slot["template"], ctx))
    return "\n\n".join(parts)
```

**不加不删。** 新增一个"认知能力"不需要改这 45 行——YAML 加一个 slot 定义 + 模板列表加一行名字。

### 1.3 一个 Slot 的三维定义

| 维度 | YAML 字段 | 语义 | 例子 |
|------|----------|------|------|
| **何时出现** | `condition` | "LLM，你现在需要考虑这个吗？" | `memory_text` — 有记忆才渲染 |
| **说什么** | `template` | "LLM，关于这件事你怎么想？" | `"## 当前主线\n{main_thread}"` |
| **排第几** | templates.slots 列表顺序 | "LLM，这个和那个哪个更重要？" | `main_thread` 在 `recent_memory` 前 |

**新增一个认知能力 = 两处 YAML。零 Python 改动。**

---

## 2. Slot 列表作为认知架构

AW 当前 13 个 slot，分三层：

**Contract 层（输出契约）— 永远激活：**
action_scope, output_contract

**World 层（环境信息）— 世界级共享：**
spatial_context, sensory_section, gate_highlight, delta_gate

**NPC 层（角色驱动）— per-agent 可配置：**
persona, main_thread, drive_values, drive_context,
recent_memory, conversation_context, behavioral_traits, intent_context

```
contract:    action_scope → "你怎么行动。"  output_contract → "输出格式。"
world:       spatial_context → "你在哪里。"  sensory_section → "周围有什么。"
             gate_highlight → "附近的门。"   delta_gate → "世界变化。"
npc:         persona → "你是谁。"           main_thread → "你的目标。"
             drive_values → "你的状态。"     drive_context → "状态边界。"
             recent_memory → "经历。"       conversation_context → "对话。"
             behavioral_traits → "倾向。"    intent_context → "上轮回顾。"
```

**这些不包含任何"怎么实现"的逻辑。** 它们只告诉 LLM "作为一个 agent 在这个世界上应该关注什么"。LLM 自己决定如何权衡这些关注点。

**不同 NPC 可以加载不同的 slot 组合。** 通过 `slot_groups.yaml` 中的 group-id（如 `full`、`pure-instinct`、`blank-slate`）和 world.yaml 中的 per-agent `npc-group:` 配置——Phoebe 可以走 `pure-instinct`（无 intent、无记忆），Monica 走 `full`。零代码——只改 YAML。

---

## 3. 引擎 vs LLM：不可逾越的线

```
引擎的职责 (Python)           LLM 的职责 (Slot 引导)
─────────────────────        ──────────────────────
世界是什么 (Entity/Layers)    我在这个世界里是谁 (persona)
世界变了吗 (Delta Gate)        我该关注什么变化 (delta_gate)
我周围有什么 (SensorySystem)  我怎么理解周围 (sensory_section)
我做过什么 (Memory)           我该记住什么 (recent_memory)
我的目标是什么 (main_thread)  我该怎么实现它 (action_guidance)
我应该输什么格式              我应该怎么决定 (全部 slot 的综合)
```

**引擎不越过这条线。** 引擎说"你周围有 3 个人"，不说"你应该跟谁说话"。引擎说"你上次做了 X"，不说"你不应该再做 X"。引擎说"世界变了"，不说"这个变化重要"。

**GA 的代码越过了这条线。** AW 把所有越线行为全部删除。留下的认知代码 = 0 行。

---

## 4. 哪些不能是 Slot

| 必须引擎 | 为什么不能是 LLM |
|---------|----------------|
| **KL Gate P/Q 比较** | 0.3s 逐帧运行，LLM 延迟 1-2s 太慢 |
| **`_write_agent_layers`** | 必须在交互时同步写入，供其他 agent 轮询 |
| **`can_interact()` 距离判定** | 物理模拟——引擎知道精确坐标 |
| **`sensory.update()` 层轮询** | 每帧 O(n) 遍历所有实体，引擎的活 |

**Slot 化的边界条件**：任何需要"实时、高频、跨多个 agent 同步"的操作留在引擎。任何"每轮 LLM 决策就能完成"的认知操作可以 slot 化。

---

## 5. 和 Generative Agents — 结对对比

| GA 的认知机制 | GA 的 Python 实现 | AW 的 Slot 等价物 | Slot 行数 |
|-------------|------------------|-------------------|---------|
| Importance scoring | Python 调 LLM 取 1-10 分，存向量库 | `main_thread` — LLM 自己维护目标字符串 | 7 |
| Memory retrieval | recency × importance × relevance 加权 | `recent_memory` — LLM 自己提取相关内容 | 4 |
| Reflection | 独立 LLM 调用 + 独立 prompt | `planning_guidance` — KL 触发时审视目标 | 10 |
| Plan | 独立 plan prompt + plan tree 数据结构 | `main_thread` + output 中的 main_thread 字段 | 12 |
| Repetition avoidance | 不存在（GA 无此机制） | `behavioral_traits` — per-agent 可配置倾向 | 8 |
| Dialogue generation | 独立 prompt + 固定输出格式 | `output_format` — 统一 JSON schema | 23 |
| Sensory input | Location tree + 视觉标注 | `sensory_prompts` YAML — 模板驱动三通道 | 14 |
| Personality | Prompt 硬编码 | `persona` slot + YAML `personality` 字段 | 3 |

**GA: ~730 行 Python 认知代码。AW: ~100 行 YAML slot + trait 定义。Assembler 的 45 行是纯字符串格式化引擎——它不知道 "hunger" 是什么，不知道 agent 有什么行为。所有认知决策（何时激活什么注意力通道、如何评估紧迫性、做什么 action）都在 YAML 里声明。**

---

## 6. v1→v7：一条"删除调度器"的直线

AgentWorld 从 v1 开始在六个大版本中持续删除"代码替 LLM 做判断"的机制：

```
v1:   graph resolver        调度"什么可以交互"
v3:   submit() chain        调度"交互怎么执行"
v4:   event_bus             调度"消息怎么传播"
v5:   action registry       调度"你能做什么"
v6:   observing state machine 调度"你该不该等"
v6:   duplication filter    调度"你是不是在重复"（v8+ 移至 per-agent traits）
v7:   sensory_prompts硬编码  调度"你看到什么"
v7.1: inbox                 调度"谁给你发消息"
```

**每删除一个调度器，LLM 就多拿回一块决策权。** 到 v7.1，引擎中唯一的"调度"只剩下 KL Gate 的 P/Q 比较——因为 LLM 做不到 0.3s 逐帧运行。

### 每次删除后都由 LLM 自然填补

| 删除 | LLM 怎么填补 |
|------|-------------|
| action registry | LLM 用自然语言描述想做什么，引擎模糊匹配目标 |
| duplication filter | LLM 看自己的 memory + per-agent trait 自主避免 |
| observing state machine | KL Gate 天然是等待机制——世界不变，Agent 不动 |
| sensory 硬编码 | YAML `sensory_prompts` 模板驱动渲染，视觉/听觉/可交互独立通道 |
| inbox | Agent 通过写层 → 他人轮询实现通信，无需消息系统 |

---

## 7. Slot 向量的普适性

**任何多 agent 系统都可以用这个模式重构认知层：**

```
传统架构:                     Slot 向量架构:
─────────                     ────────────
AgentLoop {                   Assembler.assemble(template, ctx)
  if should_plan():           for slot_name in template.slots:
    llm(plan_prompt)              if ctx[slot.condition]:
  if should_reflect():                prompt += slot.template
    llm(reflect_prompt)          llm(prompt)
  if should_evaluate():
    llm(imp_prompt)
}
```

| 传统构件 | Slot 等价 |
|---------|----------|
| 条件触发 (`should_X()`) | `condition: ctx_key` |
| 独立 prompt (`X_prompt`) | slot 的 `template` 字段 |
| 调度器 (`if/elif` 链) | templates.slots 列表顺序 |
| 数据存储 (`plan_results`) | ctx key（跨轮持久化如 `main_thread`） |

**三个转化规则**：条件触发 → ctx key 检查。独立 prompt → slot 模板。调度器 → YAML slots 列表。

---

## 8. 总结

### 这个项目在主张什么

1. **认知不是代码，是 prompt 片段的组合。** 任何"告诉 LLM 怎么想"的代码都可以被 YAML slot 替代。

2. **引擎不替 LLM 做判断。** 引擎的职责在物理层（谁在哪里、距离多远、世界变没变）。认知层（什么是重要的、该做什么、不该重复什么）全部交给 LLM，通过 slot 引导。

3. **方向永远是删除，不是添加。** 每删一个调度器，Agent 的自主性就增加一分。v1→v7 的进化证明了"少即是多"——删除 duplicaton filter 导致 LLM 自主学会避免重复（通过 memory + slot），删除 observing state machine 导致 KL Gate 天然替代等待机制。

4. **可组合性 > 系统性。** Assembler 的 45 行是纯字符串格式化引擎——它不知道 "hunger" 是什么，不知道 agent 有什么行为。所有认知决策（何时激活什么注意力通道、如何评估紧迫性、做什么 action）都在 YAML slot 里声明。对比 Generative Agents 的 730 行——包含了 retrieve、importance scoring、reflect、plan 等认知模块。不是因为 AW 更聪明——是因为"组合"天生比"系统"更灵活。新认知能力 = 新 slot，新认知架构 = 改变 slot 顺序。

### 代码量证明

| | GA | AW |
|---|-----|-----|
| 认知代码 (Python) | ~730 行 | **0 行** |
| 认知引导 (YAML) | 0 行 | **~150 行** |
| 总源文件 | — | **34 文件** |
| 总 Python 行数 | — | **~1900 行** |
| 总 YAML 行数 | — | **~880 行** |

---

## 附录：当前 Slot 完整列表（3 层，13 slot）

### Contract Layer — 输出契约
| # | Slot 名 | Condition | 用途 |
|---|---------|-----------|------|
| 1 | `action_scope` | (无条件) | action 字段语义 + 引擎交互规则 |
| 2 | `output_contract` | (无条件) | JSON schema + 字段描述 |

### World Layer — 环境信息（世界级共享）
| # | Slot 名 | Condition | 用途 |
|---|---------|-----------|------|
| 3 | `spatial_context` | `zone_name` | 空间位置 |
| 4 | `sensory_section` | `sensory_text` | 三通道感官（YAML 模板驱动） |
| 5 | `gate_highlight` | `gate_text` | 可穿越的门 |
| 6 | `delta_gate` | `delta_text` | 世界变化信号 |

### NPC Layer — 角色驱动（per-agent 可配置）
| # | Slot 名 | Condition | 用途 |
|---|---------|-----------|------|
| 7 | `persona` | `name` | 身份 + 背景 |
| 8 | `main_thread` | `main_thread` | 持久目标，LLM 自主更新 |
| 9 | `drive_values` | `drives_table` | 内在欲望数值 |
| 10 | `drive_context` | `drive_boundaries` | 数值边界参考（0/100 极值） |
| 11 | `recent_memory` | `memory_text` | 最近经历 |
| 12 | `conversation_context` | `conversation_text` | 最近对话 |
| 13 | `behavioral_traits` | `traits_text` | per-agent 行为倾向（来自 traits 矩阵） |
| 14 | `intent_context` | `last_intent` | 上轮意图回顾 + 对话不对称统计 |

slot 组通过 `slot_groups.yaml` 的二维矩阵控制——每行对应一个 group-id，每列一个 slot，0/1 控制激活。世界级通过 `world-group` 配置，NPC 通过 per-agent `npc-group` 配置。不写→继承默认 full 组。

---

*Written by Asher · 2026 · AgentWorld Async v7.1*
