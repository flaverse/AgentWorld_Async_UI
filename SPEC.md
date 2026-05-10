# SPEC — 异步 Multi-Agent 自主世界

---

## 1. 项目概述

### 1.1 核心定位

一个**纯 Python 后端 + Phaser.js 像素风前端**的异步多 Agent 自主世界引擎。  
Agent 由 LLM 驱动自主决策。世界实体由 YAML 配置驱动。  
前后端完全解耦。Agent 间通过 inbox 异步交互。与被动实体交互采用混合异步方案。

### 1.2 十大设计原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | 唯一 Entity 类 | 无子类。差异 = YAML |
| 2 | 层架构 | visual / interaction / agent / auditory 独立 Layer。层间互不知晓 |
| 3 | 层统一接口 | `see()` / `interact()` / `hear()`。动作名来自 YAML 配置 |
| 4 | 属性平权 | coins / hunger 无特殊逻辑。一切是 `apply_deltas()` |
| 5 | 位置即关系 | 同坐标多实体各自独立。无父子/容器字段 |
| 6 | 配置即行为 | Prompt / 接口 / info / rule 全部 YAML。Python 零硬编码文本 |
| 7 | Systems 总控 | 跨层逻辑唯一在 Systems 中。Entity 不做跨层 |
| 8 | 混合异步交互 | 被动实体: busy 排队 + 后台裁定。Agent 间: inbox 消息 |
| 9 | Agent 自治 | Agent 间不裁定对方。各自 LLM 决定属性变化 |
| 10 | 前端零知识 | Phaser 通用渲染器。sprite=null 不渲染。新 zone/实体只改 YAML+图 |

### 1.3 与 AgentWorld (v1) 的区别

| | AgentWorld v1 | 本项目 |
|---|--------------|--------|
| 驱动 | domain.json 预定义叙事 | Agent 欲望自主驱动 |
| 实体 | 多个 Python 子类 + adapter | 唯一 Entity + Layer 架构 |
| 时间 | 全局 tick 同步 | 各 Agent 异步独立节奏 |
| 交互 | YAML 预定义 cost/effects | LLM 裁判 + ambient_effects |
| 属性 | 字段硬编码 | 平权，无类型特权 |
| 知识 | 无 | 三层发现：亲身/观察/未知 |
| Prompt | 代码 + domain.json 混合 | 全 YAML slot 外置 |
| 空间 | zone 级粗粒度 | 网格坐标 + 双方 min 半径判定 |
| 前端 | 无 | Phaser 像素风实时渲染 |

---

## 2. 目录结构

```
06_AgentWorld_Async/
├── SPEC.md                         # 本文件
│
├── config/
│   ├── world.yaml                  # zones(tilemap) + entities(层独立配置)
│   ├── prompts.yaml                # system_prompts + templates + slots + schemas
│   └── llm.yaml                    # provider, model, api_key
│
├── src/
│   ├── layers/                     # Layer 类定义
│   │   ├── __init__.py
│   │   ├── base.py                 # Layer 基类
│   │   ├── visual.py               # VisualLayer
│   │   ├── interaction.py          # InteractionLayer + ActionDef
│   │   ├── agent.py                # AgentLayer
│   │   └── auditory.py             # AuditoryLayer
│   │
│   ├── entity/                     # 实体
│   │   ├── __init__.py
│   │   ├── entity.py               # Entity 类
│   │   └── event_entity.py         # EventEntity 类
│   │
│   ├── systems/                    # 跨层编排
│   │   ├── __init__.py
│   │   ├── sensory.py              # SensorySystem
│   │   ├── interaction.py          # InteractionSystem
│   │   └── decay.py                # DecaySystem
│   │
│   ├── agent/                      # Agent 心智
│   │   ├── __init__.py
│   │   ├── brain.py                # LLM 决策引擎
│   │   ├── memory.py               # AgentMemory
│   │   ├── drives.py               # DriveSystem
│   │   ├── sensory_memory.py       # SensoryMemory + Records
│   │   ├── knowledge.py            # AgentKnowledge
│   │   └── inbox.py                # Inbox
│   │
│   ├── interaction/                # 交互裁判
│   │   ├── __init__.py
│   │   └── resolver.py             # InteractionResolver + ActionResult
│   │
│   ├── prompt/                     # Prompt 系统
│   │   ├── __init__.py
│   │   ├── assembler.py            # Slot 组装器
│   │   ├── loader.py               # YAML 加载
│   │   └── context.py              # PromptContext
│   │
│   ├── llm/                        # LLM 客户端
│   │   ├── __init__.py
│   │   └── client.py               # LLMClient
│   │
│   ├── core/                       # 核心引擎
│   │   ├── __init__.py
│   │   ├── world.py                # World 容器
│   │   └── clock.py                # WorldClock
│   │
│   └── api/                        # API 层
│       ├── __init__.py
│       ├── server.py               # FastAPI 启动
│       ├── routes.py               # REST 路由
│       └── ws.py                   # WebSocket
│
├── web/                            # 前端 (Phaser.js)
│   ├── index.html
│   ├── css/
│   │   └── pixel.css
│   ├── js/
│   │   ├── main.js                 # Phaser 配置 + 启动
│   │   ├── scenes/
│   │   │   └── WorldScene.js       # 主场景
│   │   ├── ui/
│   │   │   ├── HUD.js              # 顶部信息栏
│   │   │   ├── EventLog.js         # 事件滚动列表
│   │   │   └── AgentPanel.js       # agent 信息面板
│   │   └── network/
│   │       ├── ws.js               # WebSocket 客户端
│   │       └── api.js              # REST 封装
│   └── assets/
│       ├── tilesets/               # 瓦片图集
│       └── sprites/                # 精灵图集
│
├── data/
│   └── world.db                    # SQLite 持久化
│
├── main.py                         # 入口
├── requirements.txt
└── .gitignore
```

---

## 3. 配置层

### 3.1 llm.yaml

```yaml
# config/llm.yaml
provider: "openai"           # openai | minimax | custom
model: "gpt-4o"              # 或 deepseek-v3, minimax-m2.7
api_key: "${OPENAI_API_KEY}" # 环境变量占位
base_url: null               # 自定义 endpoint
timeout_seconds: 60
max_retries: 2
```

### 3.2 world.yaml Schema

```yaml
world:
  name: string
  time_scale: int             # 1 真实秒 = N 模拟秒 (默认 60)
  start_time: string          # "08:00" 格式
  tick_interval_seconds: float # Agent 循环最小间隔 (默认 0.5)
  default_event_lifespan_minutes: int  # 事件实体默认存活 (默认 3)

zones: list[Zone]

Zone:
  id: string
  name: string
  width: int                  # tile 列数
  height: int                 # tile 行数
  tile_size: int              # 每 tile 像素 (默认 32)
  ambient_light: string       # hex 颜色 "#3a2a1a"
  tileset: string             # 瓦片图集名 → /assets/tilesets/{name}.png
  tilemap:
    layers: list[{name: string, data: list[int]}]   # Tiled 导出格式
    objects: list[{gid: int, x: int, y: int}]       # 静态装饰 tile
  connections: list[{gate: string, to_zone: string, target_gate: string}]

entities: list[EntityDef]

EntityDef:
  id: string
  name: string
  zone: string
  pos: [int, int]             # tile 坐标 [x, y]
  
  visual?:                    # 可选: 视觉层
    visible_radius: int       # 能被看到的最大距离
    sprite: string|null       # 前端 sprite 名。null = 不渲染
    sprite_sheet?:            # 动画帧表 (仅 agent 需)
      url: string             # → /assets/sprites/{url}
      frame_width: int
      frame_height: int
      anims: dict             # {anim_name: {row: int, frames: int}}
    info:                     # 被看到时推送给观察者的信息
      look: string            # 远观描述
      detail?: string         # 走近描述 (距离 ≤2 时推送)

  interaction?:               # 可选: 交互层
    interaction_radius: int   # 能被交互的最大距离
    public_attrs?: dict       # 👁️ 公开属性 (如 {type: "吧台", expression: "友善"})
    private_attrs?: dict      # 🔒 私有属性 (如 {price: 5, personality: "..."})
    actions: dict[string, ActionDef]  # 动作名 → 定义

  agent?:                     # 可选: Agent 层
    autonomous: bool
    speed: float              # 移速 (每格模拟分钟, 默认 1.0)
    view_radius: int          # Agent 自己的视野半径
    hearing_radius: int       # 听觉半径
    interaction_radius: int   # Agent 作为交互发起方的半径
    personality: string       # LLM 身份 prompt
    drives: dict[string, {decay: float}]
      # 欲望名: {decay: 每分钟变化量。正数=恶化,负数=自然恢复}

  auditory?:                  # 可选: 听觉层
    audible_radius: int       # 声音传播距离
    info:
      sound: string           # 听到的声音描述

  gate?:                      # 可选: Zone 传送 (type=zone_gate 时)
    to_zone: string
    to_pos: [int, int]

ActionDef:
  target_type: "passive" | "agent"
    # passive: 被动实体 → InteractionSystem 裁定
    # agent:   Agent → inbox 消息
  resolve: "rule" | "llm"
    # rule: 引擎按 rule 字段直接算
    # llm:  LLM 裁判 (仅 target_type=passive 时可用)
  params?: dict               # {param_name: {type: string, required?: bool}}
  rule?:                      # resolve=rule 时必填
    cost?: dict               # {attr: delta}  负值=消耗
    effects?: dict            # {attr: delta}  正值=获得
    duration_minutes?: int    # 交互耗时
    narrative: string         # "{caller}..." 模板
    move_to_zone?: string     # Gate 传送目标 zone
    move_to_pos?: [int, int]  # Gate 传送目标坐标
  estimated_duration?: int    # resolve=llm 时的预估耗时 (默认 5)
```

### 3.3 world.yaml 完整示例

参见 `config/world.yaml` (随项目创建)。包含:
- 1个 zone (bar_zone) 含完整 tilemap
- 2个 gate 实体
- 1个吧台 (visual + interaction)
- 2个酒 (visual + interaction, sprite=null, 同坐标)
- 1个氛围实体 (仅 visual)
- 1个硬币 (visual + interaction, sprite=null)
- 2个 NPC agent (visual + interaction + agent)

### 3.4 prompts.yaml Schema

```yaml
system_prompts: dict[string, string]
  # 系统级 prompt。key=模板名引用

templates: dict[string, TemplateDef]

TemplateDef:
  temperature: float
  slots: list[{name: string, provider: string, condition?: string}]
  output_schema: string       # → output_schemas 的 key

slots: dict[string, SlotDef]

SlotDef:
  template: string            # 模板文本。{变量} 由 provider 填充
  provider: "content" | "runtime" | "topology"
  condition?: string          # 条件名 (如 "has_memory"), 不满足跳过

output_schemas: dict[string, dict]
  # key → {type: "json_object", schema: {...}}
```

### 3.5 Output Schemas

```yaml
# Agent 决策输出
decision_output:
  type: json_object
  schema:
    thinking: string          # 推理过程
    move_to: [int, int] | null
    target_entity: string | null
    action: string | null     # 动作名 (如 "饮用")
    reply: string | null      # Agent 间回复文本
    respond_to: string | null # 回复目标 agent id

# 交互裁判输出
resolve_output:
  type: json_object
  schema:
    caller_deltas: dict       # 发起方属性变化
    target_deltas: dict       # 被调用方属性变化
    ambient_effects: list[    # 周边实体属性变化
      {entity_id: string, deltas: dict}
    ]
    narrative: string         # 完整叙事
    public_observation: string # 公开观察 (广播)
```

---

## 4. Layer 层

### 4.1 Layer 基类 — `src/layers/base.py`

```python
from dataclasses import dataclass, field

@dataclass
class Layer:
    """所有 Layer 的基类。每层只定义自己领域的抽象接口。
    层间互不知晓。跨层通信仅通过 Systems 完成。"""
    pass
```

**职责**: 提供类型标记，无共享字段。  
**依赖**: 无。  
**被调用**: 各子 Layer 继承。

### 4.2 VisualLayer — `src/layers/visual.py`

```python
from dataclasses import dataclass, field
from .base import Layer

@dataclass
class VisualLayer(Layer):
    """场景: 定义"别人看到我时获得什么信息"。
    所有实体统一调用 see()。内容差异由实例的 info 决定。"""
    
    visible_radius: int
    sprite: str | None = None
    sprite_sheet: dict | None = None
    info: dict = field(default_factory=dict)  # {look: "...", detail?: "..."}
    
    def see(self, distance: int) -> dict:
        """统一视觉入口。
        
        Args:
            distance: 观察者到本实体的曼哈顿距离
        
        Returns:
            {"look": str} 始终返回
            {"look": str, "detail": str} 距离 ≤ 2 时返回
        """
        result = {"look": self.info.get("look", "")}
        if distance <= 2 and "detail" in self.info:
            result["detail"] = self.info["detail"]
        return result
```

**依赖**: `layers.base.Layer`  
**被调用**: `SensorySystem.update()`

### 4.3 InteractionLayer — `src/layers/interaction.py`

```python
from dataclasses import dataclass, field
from enum import Enum
from .base import Layer

class TargetType(Enum):
    PASSIVE = "passive"      # 被动实体 → InteractionSystem 裁定
    AGENT = "agent"          # Agent → inbox 消息

class ResolveType(Enum):
    RULE = "rule"            # 引擎按 rule 字段直接算
    LLM = "llm"              # LLM 裁判

@dataclass
class ActionDef:
    """单个动作的完整定义。"""
    method: str                          # 动作名 (如 "饮用")
    target_type: TargetType
    resolve: ResolveType
    params: dict = field(default_factory=dict)
    rule: dict | None = None             # resolve=rule 时
    estimated_duration: int = 5          # resolve=llm 时的预估耗时

@dataclass
class InteractionLayer(Layer):
    """场景: 定义"别人能对我做什么"。
    所有实体统一调用 interact()。动作名由 YAML 定义。"""
    
    interaction_radius: int
    public_attrs: dict = field(default_factory=dict)
    private_attrs: dict = field(default_factory=dict)
    actions: dict[str, ActionDef] = field(default_factory=dict)
    
    def interact(self, action: str | None = None) -> list[str]:
        """统一交互入口。
        
        Args:
            action: 动作名。None 时返回可用动作列表。
        
        Returns:
            action=None → ["饮用", "嗅闻", ...]
        """
        if action is None:
            return list(self.actions.keys())
        raise NotImplementedError("执行动作由 InteractionSystem 负责，不在此处")
    
    def get_action(self, action: str) -> ActionDef | None:
        return self.actions.get(action)
    
    def apply_deltas(self, deltas: dict) -> None:
        """属性统一加减。无特权属性。"""
        for key, delta in deltas.items():
            self.private_attrs[key] = self.private_attrs.get(key, 0) + delta
```

**依赖**: `layers.base.Layer`  
**被调用**: `InteractionSystem` / `SensorySystem` (取动作列表)

### 4.4 AgentLayer — `src/layers/agent.py`

```python
from dataclasses import dataclass, field
from .base import Layer

@dataclass
class AgentLayer(Layer):
    """场景: 挂载 Agent 心智模块。不定义动作（动作在 InteractionLayer 中）。"""
    
    autonomous: bool = False
    speed: float = 1.0
    view_radius: int = 20
    hearing_radius: int = 15
    interaction_radius: int = 3
    personality: str = ""
    drive_rates: dict = field(default_factory=dict)
    
    # 以下不由 YAML 注入，运行时创建
    drives: object = None            # DriveSystem
    sensory: object = None           # SensoryMemory
    memory: object = None            # AgentMemory
    knowledge: object = None         # AgentKnowledge
    inbox: object = None             # Inbox
```

**依赖**: `layers.base.Layer`  
**被调用**: `SensorySystem` / `DecaySystem` / `Brain` / `Agent` 主循环

### 4.5 AuditoryLayer — `src/layers/auditory.py`

```python
from dataclasses import dataclass, field
from .base import Layer

@dataclass
class AuditoryLayer(Layer):
    """场景: 声音传播。统一 hear() 入口。"""
    
    audible_radius: int
    info: dict = field(default_factory=dict)  # {sound: "...", volume?: "..."}
    
    def hear(self, distance: int) -> dict:
        """统一听觉入口。
        
        Args:
            distance: 听者到本实体的曼哈顿距离
        
        Returns:
            {"sound": str, "volume": "响亮"|"中等"|"隐约"}
        """
        vol = "响亮" if distance <= 3 else "中等" if distance <= 8 else "隐约"
        return {
            "sound": self.info.get("sound", ""),
            "volume": vol,
        }
```

**依赖**: `layers.base.Layer`  
**被调用**: `SensorySystem.update()` (未来分支)

---

## 5. Entity 层

### 5.1 Entity — `src/entity/entity.py`

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Entity:
    """一切皆实体。无子类。差异 = layers dict。
    
    Layer 组合示例:
        吧台:   layers = {"visual": ..., "interaction": ...}
        麦酒:   layers = {"visual": ..., "interaction": ...}  (sprite=null)
        氛围:   layers = {"visual": ...}  (无可交互)
        小明:   layers = {"visual": ..., "interaction": ..., "agent": ...}
        事件:   layers = {"visual": ..., "auditory": ...}  (动态 spawn)
    """
    
    id: str
    name: str
    zone: str
    pos: list[int]                       # [x, y] grid 坐标
    layers: dict[str, Any] = field(default_factory=dict)
    
    # ── 运行时状态 ──
    status: str = "idle"                 # "idle" | "busy"
    busy_until: float | None = None      # world time
    busy_result: Any | None = None       # ActionResult
    last_action_time: float = 0.0
    
    # ── Layer 访问 ──
    def has(self, layer_name: str) -> bool:
        return layer_name in self.layers
    
    def get(self, layer_name: str):
        return self.layers.get(layer_name)
    
    # ── 空间 ──
    def distance_to(self, other: 'Entity') -> int:
        return abs(self.pos[0] - other.pos[0]) + abs(self.pos[1] - other.pos[1])
    
    def move_to(self, target_pos: list[int]) -> int:
        """移动并返回耗时 (模拟分钟)。"""
        dist = abs(self.pos[0] - target_pos[0]) + abs(self.pos[1] - target_pos[1])
        self.pos = target_pos
        agent_layer = self.get("agent")
        speed = agent_layer.speed if agent_layer else 1.0
        return int(dist * speed)
    
    # ── 属性 ──
    def apply_deltas(self, deltas: dict) -> None:
        """属性统一加减。无特权属性。
        coins / hunger / energy 完全同等对待。"""
        interaction = self.get("interaction")
        if interaction:
            interaction.apply_deltas(deltas)
    
    # ── 计算朝向 ──
    def calc_facing(self, to_pos: list[int]) -> str:
        dx = to_pos[0] - self.pos[0]
        dy = to_pos[1] - self.pos[1]
        if abs(dx) >= abs(dy):
            return "right" if dx > 0 else "left"
        else:
            return "down" if dy > 0 else "up"
```

**依赖**: `layers.*`  
**被调用**: 几乎所有模块

### 5.2 EventEntity — `src/entity/event_entity.py`

```python
from dataclasses import dataclass
from .entity import Entity

@dataclass
class EventEntity(Entity):
    """运行时动态 spawn 的临时实体。通过 SensorySystem 被其他 agent 感知。
    
    生命周期:
        ① InteractionSystem 完成后 spawn
        ② 注入 world.entities + world.active_events
        ③ 其他 agent 的 SensorySystem 自然感知到
        ④ 过期 → world.prune_events() → 从 entities 删除 → agent sensory 自然清除
    
    仅 visual + auditory 层。无 interaction 层（不可交互）。
    """
    
    spawned_at: float = 0.0
    lifespan_minutes: float = 3.0
    source_entity_id: str = ""
    source_action: str = ""
    
    def is_expired(self, now: float) -> bool:
        return (now - self.spawned_at) >= self.lifespan_minutes
```

**依赖**: `entity.entity.Entity`  
**被调用**: `World.spawn_event()` / `World.prune_events()` / `SensorySystem`

---

## 6. Systems 层

### 6.1 SensorySystem — `src/systems/sensory.py`

```python
class SensorySystem:
    """跨层代码: 读各 Layer → 写 agent.sensory_memory。
    
    所有 entity.visual 层的 see() 和 entity.auditory 层的 hear()
    经此系统收集，写入 agent.get("agent").sensory。
    Agent 决策 Prompt 从 sensory 构建，不直接接触 Entity 实例。
    """
    
    def update(self, observer: Entity, all_entities: dict[str, Entity]) -> None:
        """每轮 sense 阶段调用一次。
        
        ① 遍历所有 entity
        ② 对每个 entity 按双方半径 min 判定视觉/听觉范围
        ③ 范围内: 调用 entity.see() / entity.hear() → 写入 observer.sensory
        ④ 离开范围: 从 observer.sensory 中删除
        """
        if not observer.has("agent"):
            return
        
        agent_layer = observer.get("agent")
        sensory = agent_layer.sensory
        current_vision_ids = set()
        
        for entity in all_entities.values():
            if entity.id == observer.id:
                continue
            if entity.zone != observer.zone and not isinstance(entity, EventEntity):
                continue
            
            d = observer.distance_to(entity)
            
            # ── 视觉 ──
            if entity.has("visual"):
                visual_layer = entity.get("visual")
                see_range = min(
                    agent_layer.view_radius,
                    visual_layer.visible_radius
                )
                if d <= see_range:
                    current_vision_ids.add(entity.id)
                    is_new = entity.id not in sensory.vision
                    
                    vision_data = visual_layer.see(d)
                    
                    # 取可用的动作列表
                    actions = []
                    if entity.has("interaction"):
                        actions = entity.get("interaction").interact()
                    
                    sensory.vision[entity.id] = VisionRecord(
                        entity_id=entity.id,
                        name=entity.name,
                        pos=list(entity.pos),
                        distance=d,
                        visual_data=vision_data,
                        actions=actions,
                        can_interact=False,  # InteractionSystem 后面更新
                        first_seen=(time.time() if is_new
                                    else sensory.vision[entity.id].first_seen),
                        last_seen=time.time(),
                    )
            
            # ── 听觉 (未来) ──
            if entity.has("auditory"):
                pass  # 同模式: auditory_layer.hear(d) → sensory.hearing
        
        # 离开范围 → 删除
        for eid in list(sensory.vision.keys()):
            if eid not in current_vision_ids:
                del sensory.vision[eid]
```

**依赖**: `agent.sensory_memory.VisionRecord`, `agent.sensory_memory.HearingRecord`  
**被调用**: `Agent` 主循环的 sense 阶段  
**关键行为**: 增删更新均在此处。唯一产生/销毁感知记录的入口。

### 6.2 InteractionSystem — `src/systems/interaction.py`

```python
class InteractionSystem:
    """跨层代码: 交互判定 + 异步执行。
    
    两路分发:
      target_type=passive → submit() → Agent busy → Resolver 后台裁定
      target_type=agent   → world.send_message() → 目标 inbox
    """
    
    def __init__(self, resolver: 'InteractionResolver', 
                 derive_sound_map: dict | None = None):
        self.resolver = resolver
        self.sound_map = derive_sound_map or {}
    
    # ── 判定 ──
    def can_interact(self, agent: Entity, target: Entity) -> bool:
        """双方 interaction_radius 的 min 判定。"""
        if not target.has("interaction"):
            return False
        
        agent_r = 0
        if agent.has("agent"):
            agent_r = agent.get("agent").interaction_radius
        if agent.has("interaction"):
            agent_r = agent.get("interaction").interaction_radius
        
        target_r = target.get("interaction").interaction_radius
        return agent.distance_to(target) <= min(agent_r, target_r)
    
    def update_sensory(self, agent: Entity, all_entities: dict[str, Entity]) -> None:
        """更新 sensory_memory 中每个实体记录的 can_interact 标记。"""
        sensory = agent.get("agent").sensory
        for eid, record in sensory.vision.items():
            if eid in all_entities:
                record.can_interact = self.can_interact(agent, all_entities[eid])
    
    # ── 提交 (异步) ──
    def submit(self, interaction_id: str, agent: Entity, target: Entity,
               action: str, world: 'World') -> None:
        """提交交互请求。不阻塞。
        
        ① 标记 Agent busy
        ② 注册到 world.pending_interactions
        ③ 启动后台 _resolve_async task
        ④ 推送 WS: interaction_start
        """
        layer = target.get("interaction")
        act_def = layer.get_action(action)
        if not act_def:
            raise ValueError(f"Unknown action: {action}")
        
        if not self.can_interact(agent, target):
            raise TooFarError(f"{agent.name} too far from {target.name}")
        
        # 标记 busy
        agent.status = "busy"
        est_duration = act_def.estimated_duration
        agent.busy_until = world.clock.now() + est_duration
        
        # 后台裁定
        asyncio.create_task(
            self._resolve_async(interaction_id, agent, target, action, world)
        )
    
    def cancel(self, agent: Entity) -> None:
        """取消当前 pending 交互。"""
        agent.status = "idle"
        agent.busy_result = None
        agent.busy_until = 0.0
    
    # ── 后台裁定 ──
    async def _resolve_async(self, iid: str, agent: Entity, target: Entity,
                             action: str, world: 'World') -> None:
        """后台 task: 执行 resolve=rule 或 resolve=llm。"""
        act_def = target.get("interaction").get_action(action)
        
        if act_def.resolve == ResolveType.RULE:
            result = self._exec_rule(act_def, agent, target)
        elif act_def.resolve == ResolveType.LLM:
            ambient = world.get_ambient_entities(target, radius=2, exclude={agent.id})
            result = await self.resolver.resolve(
                caller=agent, target=target, action=action,
                ambient_entities=ambient, world=world,
            )
        else:
            raise ValueError(f"Unknown resolve type: {act_def.resolve}")
        
        # 结果投递
        agent.busy_result = result
        
        # spawn 事件实体
        self._spawn_event(world, agent, target, action, result)
        
        # WS 推送
        world.broadcast_ws({
            "event": "interaction_complete",
            "agent": agent.id, "target": target.id, "action": action,
            "observation": result.public_observation,
        })
    
    # ── Rule 执行 ──
    def _exec_rule(self, act_def: ActionDef, agent: Entity, target: Entity) -> ActionResult:
        rule = act_def.rule
        return ActionResult(
            target_id=target.id,
            caller_deltas={
                **rule.get("cost", {}),
                **rule.get("effects", {}),
            },
            target_deltas={},
            ambient_effects=[],
            narrative=rule["narrative"].format(caller=agent.name),
            public_observation=rule["narrative"].format(caller=agent.name),
            duration=rule.get("duration_minutes", 0),
            move_to_zone=rule.get("move_to_zone"),
            move_to_pos=rule.get("move_to_pos"),
        )
    
    # ── 事件实体生成 ──
    def _spawn_event(self, world, agent, target, action, result) -> None:
        sound = self.sound_map.get(action, "")
        from entity.event_entity import EventEntity
        from layers.visual import VisualLayer
        from layers.auditory import AuditoryLayer
        
        event = EventEntity(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            name=f"{agent.name}的交互",
            zone=target.zone, pos=list(target.pos),
            spawned_at=world.clock.now(),
            lifespan_minutes=world.config.get("default_event_lifespan_minutes", 3),
            source_entity_id=agent.id, source_action=action,
            layers={
                "visual": VisualLayer(
                    visible_radius=8, sprite=None,
                    info={"look": f"{agent.name}正在{action}"}
                ),
                "auditory": AuditoryLayer(
                    audible_radius=12,
                    info={"sound": sound} if sound else {},
                ) if sound else None,
            }
        )
        world.spawn_event(event)
```

**依赖**: `interaction.resolver.InteractionResolver`, `layers.interaction.*`, `entity.*`  
**被调用**: `Agent` 主循环

### 6.3 DecaySystem — `src/systems/decay.py`

```python
class DecaySystem:
    """跨层代码: 读 AgentLayer.drive_rates → 更新 DriveSystem.values。"""
    
    def tick(self, agent: Entity, elapsed_minutes: float) -> None:
        if not agent.has("agent"):
            return
        agent_layer = agent.get("agent")
        if not agent_layer.drives:
            return
        agent_layer.drives.decay(elapsed_minutes)
```

**依赖**: `agent.drives.DriveSystem`  
**被调用**: `Agent` 主循环

---

## 7. Agent 心智层

### 7.1 SensoryMemory — `src/agent/sensory_memory.py`

```python
from dataclasses import dataclass, field

@dataclass
class VisionRecord:
    """一条视觉感知记录。由 SensorySystem 写入。"""
    entity_id: str
    name: str
    pos: list[int]
    distance: int
    visual_data: dict              # VisualLayer.see() 返回
    actions: list[str]             # InteractionLayer.interact() 返回
    can_interact: bool             # InteractionSystem 更新
    first_seen: float = 0.0
    last_seen: float = 0.0

@dataclass
class HearingRecord:
    """一条听觉感知记录。由 SensorySystem 写入。"""
    entity_id: str
    name: str
    pos: list[int]
    distance: int
    auditory_data: dict            # AuditoryLayer.hear() 返回
    first_heard: float = 0.0
    last_heard: float = 0.0

@dataclass
class SensoryMemory:
    """Agent 内部。持有的当前感知汇总。
    Prompt assembler 从此读取，不接触 Entity 实例。"""
    
    vision: dict[str, VisionRecord] = field(default_factory=dict)
    hearing: dict[str, HearingRecord] = field(default_factory=dict)
    
    def get_interactable(self) -> list[VisionRecord]:
        return [r for r in self.vision.values() if r.can_interact]
    
    def get_visible_only(self) -> list[VisionRecord]:
        return [r for r in self.vision.values() if not r.can_interact]
    
    def clear(self):
        self.vision.clear()
        self.hearing.clear()

    def to_prompt_vision(self) -> str:
        """生成 LLM prompt 用的视觉文本。"""
        lines = []
        for r in self.get_interactable():
            lines.append(f"✅ {r.name} ({r.pos[0]},{r.pos[1]}) | {r.visual_data.get('look','')}")
            lines.append(f"   可做: {r.actions}")
            if "detail" in r.visual_data:
                lines.append(f"   详情: {r.visual_data['detail']}")
        for r in self.get_visible_only():
            lines.append(f"👁️ {r.name} ({r.pos[0]},{r.pos[1]}) | 距离{r.distance} | {r.visual_data.get('look','')}")
        return "\n".join(lines)
```

**依赖**: 无  
**被调用**: `SensorySystem` (写入), `Brain` / `PromptAssembler` (读取)

### 7.2 DriveSystem — `src/agent/drives.py`

```python
@dataclass
class DriveSystem:
    """Agent 欲望系统。属性平权（无特殊字段）。"""
    
    values: dict[str, float]                   # {"hunger": 70, "thirst": 80, ...}
    decay_rates: dict[str, float]              # {"hunger": +0.02, ...}
    
    def decay(self, elapsed_minutes: float) -> None:
        for key, rate in self.decay_rates.items():
            if key in self.values:
                self.values[key] += rate * elapsed_minutes
                self.values[key] = max(0.0, min(100.0, self.values[key]))
    
    def apply_deltas(self, deltas: dict) -> None:
        for key, delta in deltas.items():
            self.values[key] = self.values.get(key, 0.0) + delta
    
    def to_prompt_table(self) -> str:
        """生成 LLM prompt 用的欲望表格。"""
        lines = ["| 属性 | 数值 |", "|------|------|"]
        for key, val in self.values.items():
            urgency = "⚠️急需" if val >= 80 else "●需要" if val >= 60 else "○正常"
            lines.append(f"| {key} | {val:.0f}/100 {urgency} |")
        return "\n".join(lines)
```

**依赖**: 无  
**被调用**: `DecaySystem` (写入), `Brain` (读取)

### 7.3 AgentMemory — `src/agent/memory.py`

```python
@dataclass
class AgentMemory:
    """短期记忆。最近 N 条行动记录。Prompt 从此构建。"""
    
    entries: list[dict] = field(default_factory=list)
    max_size: int = 10
    
    def record(self, action: str, target_name: str, narrative: str) -> None:
        self.entries.append({
            "action": action,
            "target": target_name,
            "narrative": narrative,
        })
        if len(self.entries) > self.max_size:
            self.entries.pop(0)  # 最旧的出列
    
    def record_fail(self, action: str, reason: str) -> None:
        self.entries.append({
            "action": action,
            "result": "FAILED",
            "reason": reason,
        })
        if len(self.entries) > self.max_size:
            self.entries.pop(0)
    
    def recent(self, n: int = 5) -> list[dict]:
        return self.entries[-n:]
    
    def to_prompt_text(self, n: int = 5) -> str:
        entries = self.recent(n)
        if not entries:
            return "无"
        return "\n".join(
            f"- {e.get('action','?')}: {e.get('narrative', e.get('reason', '?'))}"
            for e in entries
        )
```

**依赖**: 无  
**被调用**: Agent 主循环 (写入), `Brain` (读取)

### 7.4 Inbox — `src/agent/inbox.py`

```python
@dataclass
class Message:
    """Agent 间异步消息。"""
    from_agent_id: str
    from_agent_name: str
    method: str              # 对方调用的动作名 ("交谈")
    content: str             # 消息正文
    timestamp: float

@dataclass
class Inbox:
    """消息信箱。Agent 每轮 sense 时 drain 所有消息。"""
    
    messages: list[Message] = field(default_factory=list)
    
    def send(self, from_id: str, from_name: str, method: str, content: str) -> None:
        self.messages.append(Message(
            from_agent_id=from_id,
            from_agent_name=from_name,
            method=method,
            content=content,
            timestamp=time.time(),
        ))
    
    def drain(self) -> list[Message]:
        msgs = self.messages.copy()
        self.messages.clear()
        return msgs
    
    def to_prompt_text(self) -> str:
        if not self.messages:
            return "无"
        return "\n".join(
            f"- {m.from_agent_name}: \"{m.content}\""
            for m in self.messages
        )
```

**依赖**: 无  
**被调用**: `World.send_message()` (写入), Agent 主循环 (读取)

### 7.5 AgentKnowledge — `src/agent/knowledge.py`

```python
@dataclass
class InterfaceKnowledge:
    """Agent 对某个实体某个动作的认知。"""
    entity_id: str
    entity_name: str
    action: str
    description: str | None = None           # 试过才知道
    experienced_deltas: dict | None = None   # 亲身才知道
    confidence: float = 0.0                  # 1.0=亲身, 0.3-0.7=观察
    source: str = ""                         # "direct" | "observed"

@dataclass
class AgentKnowledge:
    """世界认知库。三层: ✅亲身(1.0) / ❓观察(0.3-0.7) / 🔍未知(0)"""
    
    entries: dict[str, InterfaceKnowledge] = field(default_factory=dict)
    
    def _key(self, entity_id: str, action: str) -> str:
        return f"{entity_id}::{action}"
    
    def learn_direct(self, entity_id: str, entity_name: str, 
                     action: str, result: 'ActionResult') -> None:
        key = self._key(entity_id, action)
        self.entries[key] = InterfaceKnowledge(
            entity_id=entity_id, entity_name=entity_name,
            action=action,
            description=result.narrative,
            experienced_deltas=result.caller_deltas,
            confidence=1.0, source="direct",
        )
    
    def learn_observed(self, entity_id: str, entity_name: str,
                       action: str) -> None:
        key = self._key(entity_id, action)
        if key not in self.entries:
            self.entries[key] = InterfaceKnowledge(
                entity_id=entity_id, entity_name=entity_name,
                action=action, confidence=0.3, source="observed",
            )
        else:
            self.entries[key].confidence = min(0.7, self.entries[key].confidence + 0.2)
```

**依赖**: 无  
**被调用**: Agent 主循环 (记录)  
**用途**: 未来实现三层知识发现 (Demo 阶段可选)

### 7.6 Brain — `src/agent/brain.py`

```python
class Brain:
    """LLM 决策引擎。Template: agent_decision。
    
    Prompt 从 agent 的心智数据构建，不直接接触任何 Entity 实例。
    """
    
    def __init__(self, llm_client: 'LLMClient', assembler: 'PromptAssembler'):
        self.llm = llm_client
        self.assembler = assembler
    
    async def decide(self, context: dict) -> dict:
        """调用 LLM #1 决策。
        
        Args:
            context: 包含 round, name, personality, drives,
                     zone, pos, sensory, messages, memory, busy
        
        Returns:
            {"thinking": str, "move_to": [x,y]|null, "target_entity": str|null,
             "action": str|null, "reply": str|null, "respond_to": str|null}
        """
        prompt = self.assembler.assemble("agent_decision", context)
        system = self.assembler.get_system_prompt("agent_decision")
        schema = self.assembler.get_output_schema("agent_decision")
        
        raw = await self.llm.chat(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
        )
        return json.loads(raw)
```

**依赖**: `llm.client.LLMClient`, `prompt.assembler.PromptAssembler`  
**被调用**: `Agent` 主循环的 think 阶段

---

## 8. 交互裁判 — `src/interaction/resolver.py`

```python
@dataclass
class ActionResult:
    """交互结果。"""
    target_id: str = ""
    caller_deltas: dict = field(default_factory=dict)
    target_deltas: dict = field(default_factory=dict)
    ambient_effects: list[dict] = field(default_factory=dict)
    # ambient_effects: [{"entity_id": str, "deltas": dict}, ...]
    narrative: str = ""
    public_observation: str = ""
    duration: int = 0
    move_to_zone: str | None = None
    move_to_pos: list[int] | None = None

class InteractionResolver:
    """LLM #2 裁判。仅处理 target_type=passive + resolve=llm 的交互。
    
    Prompt 包含:
        - caller: 公开+私有状态
        - target: 公开+私有状态
        - action: 动作名
        - ambient_entities: 同位置/邻格的其他实体
    """
    
    def __init__(self, llm_client: 'LLMClient', assembler: 'PromptAssembler'):
        self.llm = llm_client
        self.assembler = assembler
    
    async def resolve(self, caller: Entity, target: Entity, action: str,
                      ambient_entities: list[dict], world: 'World') -> ActionResult:
        """调用 LLM #2 裁定交互结果。"""
        context = self._build_context(caller, target, action, ambient_entities)
        prompt = self.assembler.assemble("interaction_resolve", context)
        system = self.assembler.get_system_prompt("interaction_resolve")
        schema = self.assembler.get_output_schema("interaction_resolve")
        
        raw = await self.llm.chat(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
        )
        data = json.loads(raw)
        
        return ActionResult(
            target_id=target.id,
            caller_deltas=data.get("caller_deltas", {}),
            target_deltas=data.get("target_deltas", {}),
            ambient_effects=data.get("ambient_effects", []),
            narrative=data.get("narrative", ""),
            public_observation=data.get("public_observation", ""),
        )
    
    def _build_context(self, caller, target, action, ambient) -> dict:
        return {
            "caller_name": caller.name,
            "caller_public": (caller.get("interaction").public_attrs
                              if caller.has("interaction") else {}),
            "caller_private": (caller.get("interaction").private_attrs
                               if caller.has("interaction") else {}),
            "target_name": target.name,
            "target_public": target.get("interaction").public_attrs,
            "target_private": target.get("interaction").private_attrs,
            "action": action,
            "ambient_list": ambient,
        }
```

**依赖**: `llm.client.LLMClient`, `prompt.assembler.PromptAssembler`  
**被调用**: `InteractionSystem._resolve_async()`

---

## 9. Prompt 系统

### 9.1 PromptLoader — `src/prompt/loader.py`

```python
class PromptLoader:
    """从 YAML 加载所有 prompt 配置。"""
    
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.data = yaml.safe_load(f)
    
    def get_system_prompt(self, name: str) -> str:
        return self.data["system_prompts"].get(name, "")
    
    def get_template(self, name: str) -> dict:
        return self.data["templates"][name]
    
    def get_slot(self, name: str) -> dict:
        return self.data["slots"].get(name, {})
    
    def get_output_schema(self, name: str) -> dict:
        return self.data["output_schemas"].get(name, {})
```

**依赖**: `yaml`  
**被调用**: `PromptAssembler`

### 9.2 PromptAssembler — `src/prompt/assembler.py`

```python
class PromptAssembler:
    """Slot 组装器。三个 provider:
        content  → 静态文本模板 (from YAML)
        runtime  → Agent 实时状态 (drives, memory, messages, clock)
        topology → 附近实体列表 (from sensory_memory)
    """
    
    def __init__(self, loader: PromptLoader):
        self.loader = loader
    
    def assemble(self, template_name: str, context: dict) -> str:
        template = self.loader.get_template(template_name)
        parts = []
        
        for slot_def in template["slots"]:
            # 检查 condition
            cond = slot_def.get("condition")
            if cond and not self._check_condition(cond, context):
                continue
            
            slot = self.loader.get_slot(slot_def["name"])
            provider = slot.get("provider", "content")
            
            if provider == "content":
                text = slot["template"]
            elif provider == "runtime":
                text = self._render_runtime(slot_def["name"], slot["template"], context)
            elif provider == "topology":
                text = self._render_topology(slot_def["name"], slot["template"], context)
            else:
                text = ""
            
            if text:
                parts.append(text)
        
        return "\n\n".join(parts)
    
    def get_system_prompt(self, template_name: str) -> str:
        template = self.loader.get_template(template_name)
        ref = template.get("system_prompt_ref")
        if ref:
            # 支持点号路径: "system_prompts.agent_decision"
            return self.loader.get_system_prompt(ref)
        return ""
    
    def get_output_schema(self, template_name: str) -> dict:
        template = self.loader.get_template(template_name)
        schema_name = template.get("output_schema", "")
        return self.loader.get_output_schema(schema_name)
    
    def _check_condition(self, cond: str, context: dict) -> bool:
        """检查 slot 条件。
        has_memory → context["memory"] 有内容
        has_messages → context["messages"] 有内容
        has_ambient → context["ambient_list"] 有内容
        is_busy → context["busy"] == True
        """
        if cond == "has_memory":
            return bool(context.get("memory_text"))
        if cond == "has_messages":
            return bool(context.get("messages_text"))
        if cond == "has_ambient":
            return bool(context.get("ambient_list"))
        if cond == "is_busy":
            return context.get("busy", False)
        return True
    
    def _render_runtime(self, slot_name: str, template: str, context: dict) -> str:
        """runtime provider: 填充 Agent 实时数据。"""
        return template.format(**context)
    
    def _render_topology(self, slot_name: str, template: str, context: dict) -> str:
        """topology provider: 填充附近实体数据。"""
        return template.format(**context)
```

**依赖**: `prompt.loader.PromptLoader`  
**被调用**: `Brain`, `InteractionResolver`

### 9.3 PromptContext — `src/prompt/context.py`

```python
@dataclass
class PromptContext:
    """Agent 决策时的完整上下文。由 Agent 主循环构建。"""
    round: int = 0
    name: str = ""
    personality: str = ""
    drives_table: str = ""            # DriveSystem.to_prompt_table()
    pos_x: int = 0
    pos_y: int = 0
    zone_name: str = ""
    zone_width: int = 0
    zone_height: int = 0
    interactable_text: str = ""       # sensory.to_prompt_vision() 可交互部分
    visible_text: str = ""            # sensory.to_prompt_vision() 仅可见部分
    memory_text: str = ""             # memory.to_prompt_text()
    messages_text: str = ""           # inbox.to_prompt_text()
    busy: bool = False
    busy_action: str = ""
```

**依赖**: 无  
**被调用**: Agent 主循环 → `Brain.decide()`

---

## 10. LLM 客户端 — `src/llm/client.py`

```python
class LLMClient:
    """统一 LLM 客户端。支持 OpenAI / MiniMax / 自定义。"""
    
    def __init__(self, config: dict):
        self.provider = config.get("provider", "openai")
        self.model = config["model"]
        self.base_url = config.get("base_url")
        self.timeout = config.get("timeout_seconds", 60)
        self.max_retries = config.get("max_retries", 2)
        
        api_key = config["api_key"]
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, "")
        
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
    
    async def chat(self, system: str, messages: list[dict],
                   response_format: dict | None = None,
                   temperature: float = 0.7) -> str:
        """发送 chat completion 请求。返回文本内容。"""
        full_messages = [{"role": "system", "content": system}]
        full_messages.extend(messages)
        
        kwargs = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format
        
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self.client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as e:
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return ""
```

**依赖**: `openai`  
**被调用**: `Brain`, `InteractionResolver`

---

## 11. 核心引擎

### 11.1 WorldClock — `src/core/clock.py`

```python
class WorldClock:
    """模拟时钟。时间尺度可配。"""
    
    def __init__(self, start_time_str: str, time_scale: int):
        self.time_scale = time_scale  # 1真实秒 = N模拟秒
        self.start_real = time.time()
        self.start_sim = self._parse_time(start_time_str)
    
    def now(self) -> float:
        """返回当前模拟时间 (从 start_sim 起的模拟分钟数)。"""
        elapsed_real = time.time() - self.start_real
        elapsed_sim_seconds = elapsed_real * self.time_scale
        return elapsed_sim_seconds / 60.0  # 转换为分钟
    
    def time_str(self) -> str:
        """返回当前模拟时间的 HH:MM 字符串。"""
        total_minutes = self.now()
        base = self._parse_time("00:00")
        total = self.start_sim + total_minutes
        hours = int(total // 60) % 24
        minutes = int(total % 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def _parse_time(self, s: str) -> float:
        h, m = map(int, s.split(":"))
        return h * 60 + m
```

**依赖**: `time`  
**被调用**: `World`, Agent 主循环

### 11.2 World — `src/core/world.py`

```python
class World:
    """世界容器。持有所有实体、Zone、消息路由、事件管理。"""
    
    def __init__(self, world_config: dict, prompts_config: dict, llm_config: dict):
        self.config = world_config["world"]
        self.time_scale = self.config.get("time_scale", 60)
        self.clock = WorldClock(
            self.config.get("start_time", "08:00"),
            self.time_scale,
        )
        
        self.zones: dict[str, dict] = {}
        self.entities: dict[str, Entity] = {}
        self.active_events: dict[str, EventEntity] = {}
        self.pending_interactions: dict[str, dict] = {}
        
        # 加载 zones
        for zone_def in world_config.get("zones", []):
            self.zones[zone_def["id"]] = zone_def
        
        # 加载 entities (通过工厂)
        self._load_entities(world_config.get("entities", []))
    
    def _load_entities(self, entity_defs: list[dict]) -> None:
        """从 YAML 定义创建 Entity 实例。
        解析各层配置 → 实例化 Layer → 组装 Entity。"""
        for ent_def in entity_defs:
            entity = Entity(
                id=ent_def["id"],
                name=ent_def["name"],
                zone=ent_def["zone"],
                pos=ent_def["pos"],
            )
            
            # VisualLayer
            if "visual" in ent_def:
                v = ent_def["visual"]
                entity.layers["visual"] = VisualLayer(
                    visible_radius=v.get("visible_radius", 5),
                    sprite=v.get("sprite"),
                    sprite_sheet=v.get("sprite_sheet"),
                    info=v.get("info", {}),
                )
            
            # InteractionLayer
            if "interaction" in ent_def:
                inter = ent_def["interaction"]
                actions = {}
                for name, a in inter.get("actions", {}).items():
                    actions[name] = ActionDef(
                        method=name,
                        target_type=TargetType(a.get("target_type", "passive")),
                        resolve=ResolveType(a.get("resolve", "rule")),
                        params=a.get("params", {}),
                        rule=a.get("rule"),
                        estimated_duration=a.get("estimated_duration", 5),
                    )
                entity.layers["interaction"] = InteractionLayer(
                    interaction_radius=inter.get("interaction_radius", 2),
                    public_attrs=inter.get("public_attrs", {}),
                    private_attrs=inter.get("private_attrs", {}),
                    actions=actions,
                )
            
            # AgentLayer
            if "agent" in ent_def:
                ag = ent_def["agent"]
                agent_layer = AgentLayer(
                    autonomous=ag.get("autonomous", False),
                    speed=ag.get("speed", 1.0),
                    view_radius=ag.get("view_radius", 20),
                    hearing_radius=ag.get("hearing_radius", 15),
                    interaction_radius=ag.get("interaction_radius", 3),
                    personality=ag.get("personality", ""),
                    drive_rates={k: v.get("decay", 0) for k, v in ag.get("drives", {}).items()},
                )
                # 初始化心智
                # 从 interaction.private_attrs 复制初始欲望值
                if entity.has("interaction"):
                    init_attrs = entity.get("interaction").private_attrs
                    agent_layer.drives = DriveSystem(
                        values={k: init_attrs.get(k, 50) for k in agent_layer.drive_rates},
                        decay_rates=agent_layer.drive_rates,
                    )
                agent_layer.sensory = SensoryMemory()
                agent_layer.memory = AgentMemory()
                agent_layer.knowledge = AgentKnowledge()
                agent_layer.inbox = Inbox()
                entity.layers["agent"] = agent_layer
            
            # Gate
            if "gate" in ent_def:
                entity.layers["gate"] = ent_def["gate"]
            
            self.entities[entity.id] = entity
    
    # ── 查询 ──
    def get_zone_data(self, zone_id: str) -> dict:
        return self.zones[zone_id]
    
    def get_ambient_entities(self, center: Entity, radius: int,
                             exclude: set[str]) -> list[dict]:
        """获取 center 周围半径内的其他实体。用于 Resolver 上下文。
        返回每个实体的 name + visual info + private_attrs。"""
        ambient = []
        for entity in self.entities.values():
            if entity.id in exclude:
                continue
            if entity.zone != center.zone:
                continue
            d = center.distance_to(entity)
            if d <= radius and entity.has("visual") and entity.has("interaction"):
                ambient.append({
                    "entity_id": entity.id,
                    "name": entity.name,
                    "distance": d,
                    "visual": entity.get("visual").see(d),
                    "private_hint": entity.get("interaction").private_attrs,
                })
        return ambient
    
    # ── 消息 ──
    def send_message(self, from_id: str, to_id: str, method: str = "", 
                     content: str = "") -> None:
        """发送 Agent 间消息。写入目标 inbox。"""
        target = self.entities.get(to_id)
        if not target or not target.has("agent"):
            return
        from_entity = self.entities.get(from_id)
        from_name = from_entity.name if from_entity else from_id
        target.get("agent").inbox.send(from_id, from_name, method, content)
    
    # ── 事件实体 ──
    def spawn_event(self, event: EventEntity) -> None:
        self.active_events[event.id] = event
        self.entities[event.id] = event
    
    def prune_events(self) -> None:
        now = self.clock.now()
        expired = [eid for eid, evt in self.active_events.items()
                   if evt.is_expired(now)]
        for eid in expired:
            del self.active_events[eid]
            self.entities.pop(eid, None)
    
    # ── WebSocket ──
    def broadcast_ws(self, data: dict) -> None:
        """向所有连接的 WebSocket 客户端广播事件。"""
        # 由 ws.py 管理连接池
        from api.ws import broadcast
        asyncio.create_task(broadcast(data))
```

**依赖**: `core.clock.WorldClock`, `layers.*`, `entity.*`, `agent.*`  
**被调用**: `main.py`, Agent 主循环

---

## 12. API 层

### 12.1 REST — `src/api/routes.py`

```
GET  /api/v1/world/state?focus={agent_id}
     返回: {time: str, focus_zone: {完整 zone 数据}, entities: [全量]}
     
GET  /api/v1/agents
     返回: [{id, name, zone, pos, public_attrs, status}]
     
GET  /api/v1/agents/{id}
     返回: {id, name, zone, pos, public_attrs, memory_summary, drives_summary}

POST /api/v1/agents
     注入新 agent。Body: {id, name, zone, pos, layers: {...}}
     返回: {id, status: "spawned"}

POST /api/v1/agents/{id}/command
     人类向 agent 发指令。Body: {content: string}
     写入 agent inbox。返回: {status: "sent"}
     
GET  /api/v1/entities
     返回: [全量 entity 列表 (仅公开信息)]
```

### 12.2 WebSocket — `src/api/ws.py`

```
WS /ws/live

事件类型:
  agent_move:
    {event, agent, from:[x,y], to:[x,y], facing, duration_ms, zone}
  
  interaction_start:
    {event, agent, target, action, bubble}
  
  interaction_complete:
    {event, agent, target, action, observation}
  
  zone_change:
    {event, agent, zone:{全量}, agent_pos:[x,y], facing}
  
  world_time:
    {event, time, period, ambient_tint}
  
  entity_enter:
    {event, entity:{全量}}
  
  entity_leave:
    {event, entity_id}
```

### 12.3 前端渲染规则

```
sprite != null  → 创建 Phaser sprite (从 sprite_url 或 tileset 取)
sprite == null  → 不渲染 (逻辑存在，前后端分离)
sprite_sheet != null → 创建动画 (walk_down/up/left/right + idle)
agent_move → tween 平滑移动 + 播放 walk 动画
interaction → 精灵上方弹出气泡文字 (3秒淡出)
zone_change → Camera.fadeOut → scene.restart(newZoneData) → fadeIn
```

---

## 13. 主入口 — `main.py`

```python
async def main():
    # 1. 加载配置
    world_cfg = yaml.safe_load(open("config/world.yaml"))
    prompts_cfg = yaml.safe_load(open("config/prompts.yaml"))
    llm_cfg = yaml.safe_load(open("config/llm.yaml"))
    
    # 2. 初始化 Prompt
    loader = PromptLoader("config/prompts.yaml")
    assembler = PromptAssembler(loader)
    
    # 3. 初始化 LLM
    llm = LLMClient(llm_cfg)
    
    # 4. 初始化 World
    world = World(world_cfg, prompts_cfg, llm_cfg)
    
    # 5. 初始化 Systems
    brain = Brain(llm, assembler)
    resolver = InteractionResolver(llm, assembler)
    
    # 声音映射表
    sound_map = {
        "饮用": "杯子碰触吧台的清脆声",
        "交谈": "隐约的说话声",
        "倚靠": "木制吧台轻微的吱呀声",
        "捡起": "硬币落地的叮当声",
    }
    
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(resolver, sound_map),
        "decay": DecaySystem(),
        "assembler": assembler,
        "resolver": resolver,
    }
    
    # 6. 找出所有 autonomous entity
    agents = [e for e in world.entities.values()
              if e.get("agent") and e.get("agent").autonomous]
    
    # 7. 启动
    agent_tasks = [asyncio.create_task(agent.run(world, systems))
                   for agent in agents]
    
    # 事件清理 task
    async def prune_loop():
        while True:
            await asyncio.sleep(1)
            world.prune_events()
    prune_task = asyncio.create_task(prune_loop())
    
    # API server (可选)
    # api_task = asyncio.create_task(uvicorn.run(...))
    
    await asyncio.gather(*agent_tasks, prune_task)
```

**Agent.run() 伪代码**: 详见 Agent 主循环 (章节 14)。

---

## 14. Agent 主循环

```
┌─────────────────────────────────────────────────────┐
│              Agent.run(world, systems)               │
│                                                      │
│  while alive:                                        │
│                                                      │
│    elapsed = clock.now() - last_action_time          │
│                                                      │
│    ┌─ ① 基础更新 (不受 busy 影响) ──────────────────┐│
│    │ systems["decay"].tick(self, elapsed)            ││
│    │ systems["sensory"].update(self, world.entities) ││
│    │ systems["interaction"].update_sensory(...)      ││
│    │ messages = inbox.drain()                        ││
│    │ world.prune_events()                            ││
│    └────────────────────────────────────────────────┘│
│                                                      │
│    ┌─ ② 检查 busy_result ───────────────────────────┐│
│    │ if busy_result is not None:                     ││
│    │   apply_deltas(result.caller_deltas)            ││
│    │   target.apply_deltas(result.target_deltas)      ││
│    │   for amb in result.ambient_effects:            ││
│    │     amb_target.apply_deltas(amb["deltas"])      ││
│    │   memory.record(action, result.narrative)       ││
│    │   status = "idle"                               ││
│    │   busy_result = None                            ││
│    └────────────────────────────────────────────────┘│
│                                                      │
│    ┌─ ③ 决策 (idle 时) ─────────────────────────────┐│
│    │ if status == "idle" and clock.now() >= busy_until:│
│    │   ctx = PromptContext(                          ││
│    │     round, name, personality,                   ││
│    │     drives.to_prompt_table(),                   ││
│    │     sensory.to_prompt_vision(),                 ││
│    │     memory.to_prompt_text(),                    ││
│    │     inbox.to_prompt_text(),                     ││
│    │     busy=no, zone=..., pos=...,                 ││
│    │   )                                             ││
│    │   decision = await brain.decide(ctx)            ││
│    │                                                  ││
│    │   # ── 移动 ──                                  ││
│    │   if decision.move_to:                          ││
│    │     from_pos = self.pos                         ││
│    │     move_time = self.move_to(decision.move_to)  ││
│    │     # 移动后重新感知                             ││
│    │     systems["sensory"].update(self, ...)         ││
│    │     systems["interaction"].update_sensory()     ││
│    │     WS: agent_move                              ││
│    │                                                  ││
│    │   # ── 交互 ──                                  ││
│    │   if decision.target and decision.action:       ││
│    │     target = world.entities[decision.target]    ││
│    │     layer = target.get("interaction")           ││
│    │     act_def = layer.get_action(decision.action) ││
│    │                                                  ││
│    │     if act_def.target_type == PASSIVE:          ││
│    │       if systems["interaction"].can_interact(): ││
│    │         iid = ulid()                            ││
│    │         systems["interaction"].submit(          ││
│    │           iid, self, target, action, world)     ││
│    │       else:                                     ││
│    │         memory.record_fail("目标不在范围")       ││
│    │                                                  ││
│    │     elif act_def.target_type == AGENT:          ││
│    │       world.send_message(                       ││
│    │         self.id, target.id, action, content)    ││
│    │                                                  ││
│    │   # ── 回复消息 ──                              ││
│    │   if decision.reply and decision.respond_to:    ││
│    │     world.send_message(                         ││
│    │       self.id, decision.respond_to,             ││
│    │       "reply", decision.reply)                  ││
│    │                                                  ││
│    └────────────────────────────────────────────────┘│
│                                                      │
│    ┌─ ④ Busy 时的轻量决策 (可选) ────────────────────┐│
│    │ if status == "busy" and messages:               ││
│    │   ctx = PromptContext(..., busy=True)           ││
│    │   mini_decision = await brain.decide(ctx)       ││
│    │   if mini_decision.reply:                       ││
│    │     world.send_message(...)                     ││
│    └────────────────────────────────────────────────┘│
│                                                      │
│    ┌─ ⑤ Sleep ──────────────────────────────────────┐│
│    │ await asyncio.sleep(tick_interval)              ││
│    └────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

## 15. 数据流图

### 15.1 Agent 主循环数据流

```
                    ┌──────────┐
                    │ YAML配置  │
                    └────┬─────┘
                         ▼
              World.load_entities()
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         VisualLayer InteractionLayer AgentLayer
              │          │          │
              └──────────┼──────────┘
                         │
              SensorySystem.update()  ← 每轮 sense
                         │
                         ▼
              Agent.sensory_memory    ← 感知记忆
              Agent.drives            ← 欲望值
              Agent.memory            ← 经历记忆
              Agent.inbox             ← 消息
                         │
                         ▼
              Brain.decide(LLM #1)    ← 决策
                         │
              ┌──────────┼──────────┐
              ▼                     ▼
         move_to()           InteractionSystem
         (引擎)              ┌───────┴───────┐
                             ▼               ▼
                        passive+rule     passive+llm
                        (引擎直接算)     Resolver(LLM #2)
                             │               │
                             ▼               ▼
                        apply_deltas()   EventEntity spawn
                             │               │
                             └───────┬───────┘
                                     ▼
                            memory.record()
                            WS broadcast
                            asyncio.sleep()
```

### 15.2 被动实体交互时序

```
Agent A                 InteractionSystem          Resolver
  │                           │                       │
  ├─ decision: drink_ale.饮用  │                       │
  ├─ submit() ────────────────►│                       │
  │                            ├─ A.status = "busy"    │
  │                            ├─ WS: interaction_start│
  │                            ├─ asyncio task ───────►│
  │  (继续循环)                 │                       ├─ 收集 ambient
  │                            │                       ├─ LLM #2
  │  ├─ decay/tick             │                       ├─ 返回 result
  │  ├─ sensory.update()       │◄──────────────────────│
  │  ├─ inbox.drain()          │                       │
  │  ├─ 检查 busy_result       │                       │
  │  │  (空, 继续 sleep)       │                       │
  │  ├─ sleep(tick_interval)   │                       │
  │                            │                       │
  │  ├─ decay/sense            │                       │
  │  ├─ busy_result 到达! ────►│                       │
  │  ├─ apply_deltas()         │                       │
  │  ├─ apply ambient_effects  │                       │
  │  ├─ memory.record()        │                       │
  │  ├─ status = "idle"        │                       │
  │  ├─ think → 下一步          │                       │
  └─ ...                       │                       │
```

### 15.3 Agent 间交互时序

```
Agent A                     Agent B
  │                           │
  ├─ decision: 小明.交谈       │
  ├─ world.send_message() ────►│
  │  (立即返回，不 busy)        ├─ inbox 收到消息
  ├─ think → 做其他事           │
  │                           ├─ think (LLM #1):
  │                           │    inbox 有消息
  │                           │    decision.reply = "你好呀"
  │                           │
  ├─ inbox.drain()            │
  ├─ 收到 B 的回复             │
  ├─ think → 心情变好          │
  │  (自己 LLM 决定)           │
```

---

## 16. 实现路线

### Phase 0: 最小 Demo (验证核心闭环)

**目标**: 1 agent × 1 zone × 3 被动实体 × 5 轮 LLM 决策。控制台输出。

**涉及文件**:
```
✓ config/world.yaml     (简化版: 1 zone + 4 entity)
✓ config/prompts.yaml   (agent_decision + interaction_resolve)
✓ config/llm.yaml
✓ src/layers/base.py | visual.py | interaction.py | agent.py
✓ src/entity/entity.py
✓ src/agent/brain.py | drives.py | memory.py | sensory_memory.py | inbox.py
✓ src/systems/sensory.py | interaction.py | decay.py
✓ src/interaction/resolver.py
✓ src/prompt/loader.py | assembler.py | context.py
✓ src/llm/client.py
✓ src/core/world.py | clock.py
✓ main.py
```

**暂不包含**: event_entity, EventEntity, AgentKnowledge, frontend, API, WebSocket, 数据库, auditory layer

### Phase 1: 多 Agent + Agent 间交互

- Agent→Agent inbox 消息
- 多 Agent 并行
- EventEntity 动态事件
- 全部 systems 到位

### Phase 2: 持久化 + Knowledge

- SQLite 存 agent 状态/记忆
- AgentKnowledge 三层知识发现
- resume 续玩

### Phase 3: API + WebSocket

- FastAPI REST 路由
- WebSocket 实时事件推送
- 前后端协议定稿

### Phase 4: 前端

- Phaser.js 通用渲染器
- 像素风 tilemap + sprite + 动画
- HUD + EventLog + AgentPanel

### Phase 5: 完整配置

- 多 zone + 完整 tilemap
- 完整实体 (吧台/酒/菜单/氛围/硬币/多人)
- 所有 prompt slots

### Phase 6: 优化

- AuditoryLayer
- 碰撞系统
- 性能优化
- 文档完善

---

## 17. 附录

### 17.1 错误处理规范

```
TooFarError          : 目标不在交互范围 → memory.record_fail()
UnknownActionError   : 调用了不存在的动作 → ValueError
LLMTimeoutError      : LLM 超时 → 重试 / memory.record_fail()
ConfigError          : YAML 格式错误 → 启动时 throw
```

### 17.2 日志规范

```
格式: [TIME] [LEVEL] [MODULE] message
示例: [14:30:01] [INFO] [brain] 小明 decision: drink_ale.饮用, thinking="渴了"
```

### 17.3 命名规范

```
文件名:  snake_case  (sensory_memory.py)
类名:    PascalCase  (SensoryMemory)
方法名:  snake_case  (get_interactable())
变量名:  snake_case  (agent_layer)
常量:    UPPER_SNAKE (MAX_MEMORY_SIZE)
```

### 17.4 类型标注

所有公开方法和函数使用 Python type hints。  
关键数据类使用 `@dataclass`。

---

*SPEC version: 1.0*  
*日期: 2026-05-10*
