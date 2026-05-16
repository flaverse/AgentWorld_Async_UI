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

**AgentWorld Async: 0 行认知代码。所有"怎么思考"的决策权在 YAML 里。**

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

AW 当前 12 个 slot，每个都是对 LLM 的一条思维指令。排列顺序形成"注意力漏斗"：

```
main_thread       → "你有目标。围绕它行动。更新它。"
persona           → "记住你是谁。"
world_rules       → "世界有规则。遵守。"
kl_divergence     → "世界变了。注意这些变化。"
drive_state       → "你有欲望。满足它们。"
spatial_context   → "你在某个地方。知道在哪。"
sensory_section   → "周围有人和物。看、听、够得到什么。"
recent_memory     → "你做过一些事。记住它们。"
avoid_repetition  → "别重复自己。"
idle_guidance     → "什么都不做也是合法的选择。"
action_guidance   → "行动是自由的。引擎帮你找目标。"
output_format     → "输出JSON。这些字段是引擎需要的。"
```

**这些不包含任何"怎么实现"的逻辑。** 它们只告诉 LLM "作为一个 agent 在这个世界上应该关注什么"。LLM 自己决定如何权衡这些关注点。

**改变顺序 = 改变认知架构。** 零代码。把 `recent_memory` 移到 `main_thread` 前面，agent 就会变成"记忆驱动"而非"目标驱动"。

---

## 3. 引擎 vs LLM：不可逾越的线

```
引擎的职责 (Python)           LLM 的职责 (Slot 引导)
─────────────────────        ──────────────────────
世界是什么 (Entity/Layers)    我在这个世界里是谁 (persona)
世界变了吗 (KL Gate)          我该关注什么变化 (kl_divergence)
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
| Repetition avoidance | 不存在（GA 无此机制） | `avoid_repetition` + `idle_guidance` | 15 |
| Dialogue generation | 独立 prompt + 固定输出格式 | `output_format` — 统一 JSON schema | 23 |
| Sensory input | Location tree + 视觉标注 | `sensory_prompts` YAML — 模板驱动三通道 | 14 |
| Personality | Prompt 硬编码 | `persona` slot + YAML `personality` 字段 | 3 |

**GA: ~730 行 Python 认知代码。AW: ~88 行 YAML slot 定义。0 行 Python 认知代码。**

---

## 6. v1→v7：一条"删除调度器"的直线

AgentWorld 从 v1 开始在六个大版本中持续删除"代码替 LLM 做判断"的机制：

```
v1:   graph resolver        调度"什么可以交互"
v3:   submit() chain        调度"交互怎么执行"
v4:   event_bus             调度"消息怎么传播"
v5:   action registry       调度"你能做什么"
v6:   observing state machine 调度"你该不该等"
v6:   duplication filter    调度"你是不是在重复"
v7:   sensory_prompts硬编码  调度"你看到什么"
v7.1: inbox                 调度"谁给你发消息"
```

**每删除一个调度器，LLM 就多拿回一块决策权。** 到 v7.1，引擎中唯一的"调度"只剩下 KL Gate 的 P/Q 比较——因为 LLM 做不到 0.3s 逐帧运行。

### 每次删除后都由 LLM 自然填补

| 删除 | LLM 怎么填补 |
|------|-------------|
| action registry | LLM 用自然语言描述想做什么，引擎模糊匹配目标 |
| duplication filter | LLM 看自己的 memory + avoid_repetition slot 自主避免 |
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

4. **可组合性 > 系统性。** 一个 45 行的 Assembler + 12 个 YAML slot 可以替代 GA 的 730 行认知代码。不是因为 AW 更聪明——是因为"组合"天生比"系统"更灵活。新认知能力 = 新 slot，新认知架构 = 改变 slot 顺序。

### 代码量证明

| | GA | AW |
|---|-----|-----|
| 认知代码 (Python) | ~730 行 | **0 行** |
| 认知引导 (YAML) | 0 行 | **~88 行** |
| 总源文件 | — | **33 文件** |
| 总 Python 行数 | — | **~1800 行** |
| 总 YAML 行数 | — | **~820 行** |

---

## 附录：当前 Slot 完整列表

| # | Slot 名 | Condition | 用途 |
|---|---------|-----------|------|
| 1 | `main_thread` | `main_thread` | 持久目标驱动，LLM 自主更新 |
| 2 | `persona` | `name` | 身份 + 背景 |
| 3 | `world_rules` | (无条件) | 世界法则 |
| 4 | `kl_divergence` | `kl_text` | 世界变化信号 |
| 5 | `drive_state` | `drives_table` | 内在欲望 |
| 6 | `spatial_context` | `zone_name` | 空间位置 |
| 7 | `sensory_section` | `sensory_text` | 三通道感官（YAML 模板驱动） |
| 8 | `recent_memory` | `memory_text` | 最近经历 |
| 9 | `avoid_repetition` | `memory_text` | 防重复 |
| 10 | `idle_guidance` | `memory_text` | 教 LLM 输出 null |
| 11 | `action_guidance` | (无条件) | 行动规则 |
| 12 | `output_format` | (无条件) | JSON schema |

---

*Written by Asher · 2026 · AgentWorld Async v7.1*
