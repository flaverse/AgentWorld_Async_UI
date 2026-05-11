#!/usr/bin/env python3
"""Generate two PDFs: Technical (professional) + Plain (通俗).
Uses fpdf2. Output to /home/asher/Documents/01_Projects/06_AgentWorld_Async/docs/
"""
import os, sys, textwrap
from fpdf import FPDF

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
os.makedirs(OUT_DIR, exist_ok=True)

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"
if not os.path.exists(FONT_PATH):
    for root, _, files in os.walk("/usr/share/fonts"):
        for f in files:
            if "NotoSansCJK" in f and "Regular" in f:
                FONT_PATH = os.path.join(root, f); break

class PDF(FPDF):
    def __init__(self, title):
        super().__init__('P', 'mm', 'A4')
        self.add_font("CN", "", FONT_PATH)
        self.add_font("CN", "B", FONT_PATH.replace("Regular","Bold") if "Regular" in FONT_PATH else FONT_PATH)
        self.set_auto_page_break(True, 15)
        self.title_text = title
        self.section_count = 0
        self.add_page()

    def header(self):
        if self.page_no() == 1:
            self.set_font("CN", "B", 22)
            self.cell(0, 15, self.title_text, align="C", new_x="LMARGIN", new_y="NEXT")
            self.line(self.l_margin, self.y, self.w - self.r_margin, self.y)
            self.ln(8)
        else:
            self.set_font("CN", "", 7)
            self.set_text_color(128)
            self.cell(0, 5, self.title_text, align="L")
            self.cell(0, 5, f"p.{self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0)

    def footer(self):
        self.set_y(-12)
        self.set_font("CN", "", 7)
        self.set_text_color(128)
        self.cell(0, 8, "AgentWorld Async  |  Confidential", align="C")
        self.set_text_color(0)

    def h1(self, text):
        self.section_count += 1
        self.ln(4)
        self.set_font("CN", "B", 16)
        self.cell(0, 10, f"{self.section_count}. {text}", new_x="LMARGIN", new_y="NEXT")
        self.line(self.l_margin, self.y, self.w - self.r_margin, self.y)
        self.ln(4)

    def h2(self, text):
        self.ln(2)
        self.set_font("CN", "B", 12)
        self.set_fill_color(240, 240, 250)
        self.cell(0, 8, f"  {text}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body(self, text):
        self.set_x(self.l_margin)
        self.set_font("CN", "", 9)
        self.multi_cell(0, 5, text, align='L')
        self.ln(1)

    def code_block(self, text, lang=""):
        self.ln(2)
        self.set_font("CN", "", 7)
        self.set_fill_color(245, 245, 245)
        lines = text.split("\n")
        for line in lines:
            self.cell(self.w - 2*self.l_margin, 4, "  " + line[:110], fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("CN", "", 9)
        self.set_x(self.l_margin)
        self.ln(2)

    def ascii_diagram(self, text):
        """Render a pre-formatted ASCII diagram."""
        self.ln(2)
        self.set_font("CN", "", 6.5)
        self.set_fill_color(250, 250, 255)
        lines = text.split("\n")
        for line in lines:
            clean = line[:115].replace('\u25ba', '>').replace('\u25c4', '<').replace('\u2192', '->').replace('\u2190', '<-')
            self.cell(self.w - 2*self.l_margin, 3.8, " " + clean, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("CN", "", 9)
        self.set_x(self.l_margin)
        self.ln(2)

    def table(self, headers, rows, col_widths=None):
        if not col_widths:
            col_widths = [(self.w - 2*self.l_margin) / len(headers)] * len(headers)
        # Ensure total width fits within page
        total_w = sum(col_widths)
        if total_w > self.w - 2*self.l_margin:
            scale = (self.w - 2*self.l_margin) / total_w
            col_widths = [w * scale for w in col_widths]
        self.ln(2)
        # Header
        self.set_font("CN", "B", 8)
        self.set_fill_color(50, 50, 80)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align='C')
        self.ln()
        self.set_text_color(0)
        # Rows
        self.set_font("CN", "", 8)
        for ri, row in enumerate(rows):
            if ri % 2 == 0:
                self.set_fill_color(245, 245, 250)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, str(cell)[:60], border=1, fill=True, align='C')
            self.ln()
        self.ln(2)

    def bullet(self, text, indent=0):
        self.set_font("CN", "", 9)
        prefix = "  " * indent + "- "
        w = self.w - 2*self.l_margin - indent*3
        self.multi_cell(w, 5, prefix + text)


# =======================================
# Professional Edition Content
# =======================================

def build_professional():
    pdf = PDF("AgentWorld Async — 完整技术架构")

    pdf.h1("系统全景")
    pdf.body("AgentWorld Async 是一个异步、分层架构、LLM 驱动的多 Agent 自主世界引擎。前后端通过 REST JSON + WebSocket 事件协议完全解耦。")
    pdf.ascii_diagram("""
+--------------+     REST + WS JSON     +--------------------------------+
|  Frontend    |<---------------------->|         Python Backend          |
|  (Phaser.js  |                        |                                |
|   or Godot)  |                        |  +---------+  +--------------+ |
|              |                        |  | Layers  |  |   Systems    | |
|  Pixel Map   |                        |  | Visual  |  | Sensory      | |
|  Sprites     |                        |  | Interact|  | Interaction  | |
|  HUD         |                        |  | Agent   |  | Decay        | |
|  Event Log   |                        |  | Auditory|  |              | |
|              |                        |  +----+----+  +------+-------+ |
|              |                        |       |              |         |
|              |                        |  +----+--------------+-------+ |
|              |                        |  |     Entity (Layer容器)     | |
|              |                        |  |  id+name+zone+pos+layers  | |
|              |                        |  +------------+--------------+ |
|              |                        |               |                |
|              |                        |  +------------+--------------+ |
|              |                        |  |      Agent Mind           | |
|              |                        |  |  Brain(LLM#1) Drives      | |
|              |                        |  |  Memory Inbox Knowledge   | |
|              |                        |  +---------------------------+ |
|              |                        |                                |
|              |                        |  * LLM #1: Agent Decision     |
|              |                        |  * LLM #2: Interaction Judge  |
|              |                        |  外部Agent: REST/WS接入        |
+--------------+                        +--------------------------------+
""")

    pdf.h1("Layer 层架构")
    pdf.body("每个 Entity 持有独立 Layer 字典。每层暴露一个统一抽象方法，内容全部来自 YAML 配置。层间互不知晓，跨层通信唯一通过 Systems 完成。")

    pdf.table(
        ["Layer", "文件", "统一方法", "内容来源", "谁调用"],
        [
            ["VisualLayer", "src/layers/visual.py", "see(distance) -> {look, detail}", "YAML visual.info", "SensorySystem"],
            ["InteractionLayer", "src/layers/interaction.py", "interact(action?) -> 动作列表", "YAML interaction.actions", "InteractionSystem / SensorySystem"],
            ["AgentLayer", "src/layers/agent.py", "(无抽象方法, 心智挂载点)", "YAML agent.*", "Agent 主循环"],
            ["AuditoryLayer", "src/layers/auditory.py", "hear(distance) -> {sound, volume}", "YAML auditory.info", "SensorySystem"],
        ],
        [38, 38, 50, 34, 38]
    )

    pdf.h2("InteractionLayer 动作定义")
    pdf.code_block("""# config/world.yaml
actions:
  饮用:                          # 动作名 = 纯 YAML 字符串
    target_type: passive         # passive -> 系统裁定, agent -> inbox
    resolve: llm                 # llm -> LLM #2 裁判, rule -> 引擎直接算
    estimated_duration: 10""")

    pdf.h1("Entity 模型")
    pdf.body("一切皆 Entity。无子类。差异仅在 YAML 中挂载了哪些 Layer。同坐标多实体各自独立，无父子/容器字段。")
    pdf.table(
        ["实体", "layers", "示例"],
        [
            ["吧台", "visual + interaction", "sprite有, actions: 搭话/倚靠"],
            ["麦酒", "visual + interaction", "sprite=null(不渲染), 同坐标[7,2]"],
            ["杰洛特", "visual + interaction + agent", "autonomous=true, drives"],
            ["事件实体", "visual + auditory", "动态spawn, 3分钟自动过期"],
            ["Gate", "visual + interaction", "离开-> move_to_zone"],
        ],
        [38, 55, 105]
    )

    pdf.h1("Systems 编排层")
    pdf.body("Systems 是唯一有跨层逻辑的地方。Entity 不做跨层。三个 System 各自职责清晰。")

    pdf.h2("SensorySystem — 感知")
    pdf.ascii_diagram("""
for each entity in all_entities:
    d = observer.distance_to(entity)
    
    if entity.has("visual"):                         # 读 target 的 VisualLayer
        see_range = min(observer.view_radius,        # 读 observer 的 AgentLayer
                        entity.visible_radius)       # 双方 min 判定
        if d <= see_range:
            data = entity.get("visual").see(d)        # 统一入口
            observer.sensory.vision[id] = VisionRecord(data, ...)
    
    if entity.has("auditory"):                        # 读 target 的 AuditoryLayer
        hear_range = min(observer.hearing_radius,
                         entity.audible_radius)
        if d <= hear_range:
            data = entity.get("auditory").hear(d)     # 统一入口
            observer.sensory.hearing[id] = HearingRecord(data, ...)

离开范围 -> sensory 自动删除
""")

    pdf.h2("InteractionSystem — 三模式交互")
    pdf.ascii_diagram("""
+- 判定 --------------------------------------------------+
| can_interact(agent, target)                              |
|   -> min(agent_r, target_r) >= distance                   |
+- 执行 --------------------------------------------------+
| submit()                                                 |
|   +- target_type=passive, resolve=rule                   |
|   |   -> _exec_rule()  直接应用 cost + effects             |
|   |                                                      |
|   +- target_type=passive, resolve=llm                    |
|   |   -> _resolve_async()                                 |
|   |      | 收集 ambient_entities (半径2内的其他实体)       |
|   |      | 组装 Resolver Prompt: caller私有+target私有     |
|   |      |   + 周边实体状态                               |
|   |      | LLM #2 -> caller_deltas + target_deltas        |
|   |      |        + ambient_effects + narrative           |
|   |      +-> agent.busy_result                            |
|   |                                                      |
|   +- target_type=agent                                   |
|       -> world.send_message() -> 目标 inbox                 |
|       目标自己 LLM #1 决定属性变化                        |
+----------------------------------------------------------+
""")

    pdf.h1("Agent 主循环")
    pdf.ascii_diagram("""
while alive:
    ① DECAY    DecaySystem.tick(agent, elapsed)
               -> drives.attrs × decay_rates
               
    ② SENSE    SensorySystem.update(agent, all_entities)
               InteractionSystem.update_sensory() -> can_interact标记
               inbox.drain()  -> 消息列表
               
    ③ CHECK    if agent.busy_result != None:
               -> InteractionSystem.apply_result()
               -> agent.status = "idle"
               
    ④ THINK    if agent.status == "idle":
               LLM #1:  drives + sensory + memory + inbox -> Decision
               -> {thinking, move_to?, target_entity?, action?}
               
    ⑤ MOVE     if decision.move_to:
               -> agent.move_to(duration = distance × speed)
               -> sensory 立即更新
               
    ⑥ INTERACT if decision.target + decision.action:
               -> InteractionSystem.submit()
               -> agent busy, 后台裁定
               
    ⑦ REPLY    if decision.reply:
               -> world.send_message() -> 对方 inbox
               
    ⑧ WAIT     asyncio.sleep(action_duration / time_scale)
    """)

    pdf.h1("LLM 调用边界")
    pdf.body("仅 2 个 LLM 调用点。其他全部是确定性引擎计算。")
    pdf.table(
        ["调用点", "触发条件", "Template", "输入", "输出"],
        [
            ["LLM #1 (Brain.decide)", "agent idle 时每轮必调", "agent_decision", "身份+欲望表+可交互/可见实体+记忆+消息", "{thinking, move_to?, target_entity?, action?}"],
            ["LLM #2 (Resolver.resolve)", "resolve=llm 时调", "interaction_resolve", "caller私有+target私有+动作+周边实体", "{caller_deltas, target_deltas, ambient_effects, narrative}"],
        ],
        [38, 42, 32, 40, 46]
    )

    pdf.h2("LLM #2 裁判 Prompt 结构")
    pdf.code_block("""## 发起方: 杰洛特
公开: {"expression": "冷静警惕"}
私有: {"coins": 150, "thirst": 71, "mood": 50}

## 被调用方: 麦酒
公开: {}
私有: {"price": 5, "quality": "普通"}

## 动作: 饮用

## 周边实体 (同位置或邻格)
  - 吧台(距离0): 视=木制吧台, 状态={"personality": "矮人老板", "mood": 60}
  - 葡萄酒(距离0): 视=深红色葡萄酒, 状态={"price": 12, "quality": "上等"}

## 裁定原则
- 周边实体可能影响交互(如老板在场，不付钱会被察觉)
- 你可以修改周边实体的属性(ambient_effects)
- coins不能为负""")

    pdf.h1("数据流图")
    pdf.h2("被动实体交互 (喝麦酒)")
    pdf.ascii_diagram("""
Agent                InteractionSystem            LLM #2 Resolver
  |                        |                          |
  + think -> 喝麦酒          |                          |
  + submit() -------------->|                          |
  |                         + status = "busy"          |
  |                         + ambient: [吧台{mood:60}] |
  |                         +--_resolve_async()------->|
  |  (继续循环)              |                          + 组装 prompt
  |  + decay/sense          |                          + LLM 调用
  |  + check busy_result    |<----- return ------------|
  |  |  (空, 继续)          |                          |
  |  + sleep(0.5s)          |                          |
  |                         |                          |
  |  + decay/sense          |                          |
  |  + busy_result 到达! <--|                          |
  |  + apply_deltas()       |                          |
  |  + ambient_effects       |                          |
  |  |  -> 吧台.mood +2      |                          |
  |  + memory.record()      |                          |
  |  + status = "idle"      |                          |
""")

    pdf.h2("Agent 间交互 (inbox)")
    pdf.ascii_diagram("""
老王                             小明
  |                                |
  + think -> 找小明交谈              + (正在喝酒, busy)
  + world.send_message() --------> |
  |  (不 busy, 继续)               + inbox 收到消息
  |                                |
  + sleep                          + think (busy 中仍能 think)
  |                                + -> decision.reply = "哟老王!"
  |                                + world.send_message() ---> 老王 inbox
  |                                + mood +5 (自己的 LLM 决定)
  |                                |
  + inbox 收到回复                  |
  + think -> "聊得不错"              |
  + mood +8 (自己的 LLM 决定)        |

双方属性都由各自的 LLM #1 决定。外部无裁定。
""")

    pdf.h1("API 协议")
    pdf.h2("REST 端点")
    pdf.table(
        ["方法", "路径", "说明", "请求体"],
        [
            ["GET", "/api/v1/world/state?focus={id}", "初始加载: zones + entities 全量", "—"],
            ["POST", "/api/v1/agents", "注册外部 agent", "{id, name, zone, pos, personality}"],
            ["POST", "/api/v1/agents/{id}/move", "移动 entity", "{to: [x,y]}"],
            ["POST", "/api/v1/agents/{id}/interact", "交互", "{target_entity, action}"],
            ["POST", "/api/v1/agents/{id}/sensory", "拉取感知", "—"],
            ["POST", "/api/v1/agents/{id}/command", "人类指令->inbox", "{content}"],
            ["GET", "/api/v1/errors", "错误收集器状态", "—"],
            ["DELETE", "/api/v1/errors", "清空错误记录", "—"],
        ],
        [20, 50, 72, 56]
    )

    pdf.h2("WebSocket 事件")
    pdf.table(
        ["事件", "方向", "关键字段"],
        [
            ["agent_move", "后端->前端", "agent, from, to, facing, duration_ms, zone"],
            ["interaction_start", "后端->前端", "agent, target, action, bubble"],
            ["interaction_complete", "后端->前端", "agent, target, observation"],
            ["zone_change", "后端->前端", "agent, zone (完整数据), agent_pos"],
            ["world_time", "后端->前端", "time, period, ambient_tint"],
        ],
        [48, 34, 116]
    )

    pdf.h1("配置驱动系统")
    pdf.body("Python 代码零硬编码文本。世界/行为/Prompt 全部 YAML 驱动。换一套 YAML = 换一个世界。")
    pdf.table(
        ["配置文件", "大小", "内容"],
        [
            ["config/world.yaml", "~500 lines", "zones(tilemap) + entities(分层独立配置)"],
            ["config/prompts.yaml", "~170 lines", "system_prompts + templates + slots + output_schemas"],
            ["config/llm.yaml", "~8 lines", "provider, model, api_key"],
        ],
        [44, 34, 120]
    )

    pdf.h2("prompts.yaml 结构")
    pdf.code_block("""system_prompts:
  agent_decision: "你是一个虚拟世界中的自主居民..."
  interaction_resolve: "你是世界交互裁判..."

templates:
  agent_decision:
    temperature: 0.7
    slots:                          # 有序 slot 列表
      - {name: time_info,        provider: runtime}
      - {name: persona,          provider: runtime}
      - {name: drive_state,      provider: runtime}
      - {name: spatial_context,  provider: topology}
      - {name: interactable_section, provider: topology}
      - {name: visible_section,  provider: topology, condition: "has_visible"}
      - {name: recent_memory,    provider: runtime, condition: "has_memory"}
      - {name: action_guidance,  provider: content}
      - {name: output_format,    provider: content}
    output_schema: decision_output

slots:                              # 每个 slot 独立定义
  drive_state:
    provider: runtime               # runtime = Agent 实时数据
    template: |
      ## 你的状态
      {drives_table}

output_schemas:                     # LLM 输出 JSON Schema
  decision_output:
    type: json_object
    schema:
      type: object
      properties:
        thinking: {type: string}
        move_to: {type: array}
        target_entity: {type: string}
        action: {type: string}""")

    pdf.h1("错误处理架构")
    pdf.body("集中式 ErrorCollector 收集所有模块的错误。去重、记数、带 traceback。API 暴露 GET /api/v1/errors 实时查看。")
    pdf.ascii_diagram("""
任何模块出错 -> core.error_collector.errors.log_xxx()
                     |
                     +- 去重: 同 (module, message) 合并 count++
                     +- 记录: traceback + timestamp
                     +- API: GET /api/v1/errors -> JSON 摘要

防护点:
  interaction.py -> .add_done_callback() 防异步任务死锁
  brain.py       -> LLM JSON parse 失败记录
  resolver.py    -> 裁判 JSON parse 失败记录
  client.py      -> 凭证解析 + LLM 重试全部记录
  routes.py      -> @safe_handler 装饰器包裹所有 6 个端点
  external.py    -> submit() 错误 -> WS error 响应
""")

    pdf.h1("Godot 前端计划")
    pdf.body("当前前端为 Phaser.js 像素风网页版。计划迁移至 Godot 4.x 引擎，后端一行代码不改。")
    pdf.table(
        ["维度", "Phaser.js (当前)", "Godot (计划)"],
        [
            ["精灵渲染", "彩色方块 + emoji 文本", "像素精灵图集 + AnimatedSprite 多帧动画"],
            ["动画", "tween 硬算", "AnimationPlayer 原生支持"],
            ["碰撞检测", "无", "Area2D + CollisionShape2D"],
            ["地图编辑", "手写 YAML 坐标", "Tiled 编辑器 -> .tmx 直接导入"],
            ["UI", "手写 div + CSS", "Control 节点树 (原生 UI 系统)"],
            ["导出平台", "仅浏览器", "浏览器 / Windows / Mac / Linux / iOS / Android"],
            ["网络通信", "fetch() + WebSocket (JS 原生)", "HTTPRequest 节点 + WebSocketPeer"],
            ["开发语言", "JavaScript", "GDScript (语法极似 Python)"],
        ],
        [32, 48, 118]
    )
    pdf.body("迁移改动量: 删除 web/ 目录, 新建 godot_frontend/ 目录。Python 后端全部不变。")

    pdf.h1("技术栈")
    pdf.table(
        ["Layer", "Technology"],
        [
            ["Runtime", "Python 3.12 + asyncio"],
            ["LLM", "DeepSeek Chat / MiniMax M2.7"],
            ["HTTP", "FastAPI + uvicorn"],
            ["WebSocket", "Starlette WebSocket"],
            ["Config", "YAML (PyYAML)"],
            ["Error", "ErrorCollector (内置)"],
            ["Frontend (当前)", "Phaser.js 3 (pixel art)"],
            ["Frontend (计划)", "Godot 4.x (GDScript)"],
            ["Fontend API", "REST JSON + WebSocket JSON"],
        ],
        [40, 158]
    )

    return pdf


# =======================================
# Plain Language Edition Content
# =======================================

def build_plain():
    pdf = PDF("AgentWorld Async — 通俗架构说明")

    pdf.h1("这是什么？")
    pdf.body("一个用 Python 写的虚拟世界。里面的人（Agent）会自己决定做什么——渴了去喝酒、累了坐下、看见朋友过去聊天。不用人操控。")

    pdf.body("背后用 AI（DeepSeek / MiniMax）当大脑。每个 Agent 内部有一个 AI 帮他判断：\"我现在很渴，旁边有个酒吧，酒 5 块钱一杯，我有 30 块钱，要不要买一杯？\"")

    pdf.h1("三个比喻理解核心")
    pdf.h2("比喻 1：Layer 像功能外套")
    pdf.body("每个人/物都有几件\"功能外套\"。吧台穿了两件：一件让别人能看到它（visual），一件让别人能跟它交互（interaction）。酒也穿了两件，但\"看到它\"那件外套比较小——要离得很近才能看见那杯酒。")
    pdf.body("Agent（杰洛特）多穿了一件\"自主外套\"（agent）——他会自己走路、自己决策。")

    pdf.h2("比喻 2：Entity 像通用容器")
    pdf.body("世界里的所有东西——吧台、麦酒、杰洛特、叶奈法、公告板——全部用同一个盒子来装。区别只是盒子里放了哪些功能外套。")
    pdf.body("这意味着你要加一颗\"苹果\"进去，不需要写苹果类。只需要在 YAML 文件里写：苹果在什么位置、有什么外套、能做什么。零代码。")

    pdf.h2("比喻 3：Systems 像调度中心")
    pdf.body("外套之间不互相联系。visual 外套不知道 interaction 外套的存在。所有的\"跨外套\"操作——比如\"我看到一个东西\"需要同时查 visual 外套和我的自主外套——交给 Systems 来处理。")
    pdf.body("这就像机场调度塔：飞行员不直接跟地勤对话，全通过塔台。")

    pdf.h1("杰洛特的一天（一步一步）")
    pdf.body("初始状态：杰洛特在广场 (7,5)，thirst=71（渴了），coins=150（有钱）。")

    pdf.ascii_diagram("""
* 第 1 步 — 感知 (SENSE)
  SensorySystem 扫描周围所有实体：
    * 水井 (7,6) — 可以打水
    o 酒馆入口 (13,5) — 距离 6，看得见够不着
    o 商人摊位 (10,3) — 距离 5

* 第 2 步 — 决策 (LLM #1)
  杰洛特的 AI 大脑收到这些信息 + 自己的状态：
    "我渴了 (thirst=71)，旁边有水井。先去打水喝，再去酒馆喝一杯解乏。"
  输出: { move_to: [7,6], target_entity: "square_well", action: "打水" }

* 第 3 步 — 执行
  -> 移动: [7,5] -> [7,6]
  -> 交互: 打水 (resolve=rule -> 引擎直接算 -> thirst -30)

* 第 4 步 — 再决策
  thirst=41（不渴了）。fun=22（无聊）。social=25（孤单）。
  "去酒馆喝一杯，顺便看看公告板。"
  输出: { move_to: [13,5] }

* 第 5 步 — 进酒馆
  走到酒馆入口 -> 交互: "进入酒馆"
  -> gate 传送: zone=bar_zone, pos=(1,4)
  -> sensory 清空重建 -> 看到吧台、麦酒、丹德里恩

* 第 6 步 — 喝麦酒
  在吧台前 -> 交互: 麦酒.饮用
  -> LLM #2 裁判介入:
    看到: 杰洛特(thirst=41,coins=150) + 麦酒(price=5)
    + 吧台(老板在,mood=60)
  -> 裁定: {thirst:-20, coins:-5, mood:+5}
  -> 同时: 吧台老板 mood+2（客人付钱了）
""")

    pdf.h1("喝麦酒到底发生了什么？")
    pdf.body("分两条线同时进行：")

    pdf.h2("前台（杰洛特自己的循环）")
    pdf.body("① 决策: \"喝麦酒\" -> 提交交互 -> 标记自己为 \"busy\"（不能同时做别的事）")
    pdf.body("② busy 期间: 继续呼吸（decay）、继续看周围（sense）、收发 inbox 消息。但不能再移动或新交互。")
    pdf.body("③ 收到裁判结果: 应用属性变化（thirst-20, coins-5）-> 记录记忆 -> 标记 idle")

    pdf.h2("后台（InteractionSystem）")
    pdf.body("① 收集周边实体: \"麦酒旁边是吧台，吧台后面是矮人老板，老板 mood=60\""  )
    pdf.body("② 组装裁判 Prompt: 杰洛特的私有状态 + 麦酒的私有状态 + 周边实体信息")
    pdf.body("③ AI 裁判裁定: \"杰洛特付出 5 块钱，喝下麦酒。老板看到客人付钱，心情好了一点。\"")
    pdf.body("④ 结果投递到杰洛特的 busy_result -> 前台循环处理")

    pdf.h1("外部 Agent 怎么接入？（3 步）")
    pdf.ascii_diagram("""
+--------------------------------------------------------+
|  你的程序（任意语言）           Python 后端              |
|                              AgentWorld Async          |
|                                                       |
|  ① POST /api/v1/agents  ----> register_external_agent |
|     {                                        |        |
|       id:"triss",                            |        |
|       name:"特莉丝",                           |        |
|       zone:"square",                         |        |
|       pos:[8,4]                              |        |
|     }                                        v        |
|                                        创建 Entity     |
|  ② POST /agents/triss/sensory --> 返回:               |
|                                     *商人摊位         |
|                                     o杰洛特           |
|                                        |              |
|  ③ POST /agents/triss/interact -->   |              |
|     {target:"square_bar_gate",  InteractionSystem      |
|      action:"进入酒馆"}              .submit()          |
|                                      ↓                 |
|                                     传送至 bar_zone     |
+--------------------------------------------------------+
""")

    pdf.h1("前端看什么")
    pdf.body("浏览器打开可以看到一个像素风格的地图。每个小人是彩色方块，走动时会有平滑动画。小人头上会弹出气泡文字。右边有事件日志滚动。")
    pdf.body("前端对世界内容一无所知。它只是按后端推送的 JSON 来摆 tile 和画精灵。加了新 zone、新实体、新精灵——前端一行代码不用改。")

    pdf.h1("和旧版 AgentWorld (v1) 的区别")
    pdf.table(
        ["", "v1", "v2 (现在)"],
        [
            ["时间", "回合制: 所有人同时行动", "异步: 各走各的节奏"],
            ["Agent 怎么动", "LLM 输出图操作指令", "LLM 叙事决策 + 引擎执行"],
            ["交互谁决定", "预定义的cost/effects", "LLM 裁判见双方私有状态裁定"],
            ["实体定义", "多个 Python 子类", "唯一 Entity + Layer, 纯 YAML"],
            ["关系", "图边 (npc->item qty=5)", "位置 (同坐标 = 有关联, 无父子)"],
            ["前端", "脚本输出 -> REPORT.md", "Phaser.js 像素风实时渲染"],
        ],
        [34, 70, 86]
    )

    pdf.h1("怎么加新东西？")
    pdf.body("三个例子展示\"零代码新增\"：")

    pdf.h2("例子 1: 加一碟花生")
    pdf.code_block("""# config/world.yaml
- id: peanuts
  name: "花生"
  zone: bar_zone
  pos: [7, 3]                       # 吧台旁边
  visual:
    visible_radius: 3
    sprite: null
    info: {look: "一碟盐烤花生"}
  interaction:
    interaction_radius: 2
    private_attrs: {price: 2}
    actions:
      吃:
        target_type: passive
        resolve: rule
        rule:
          effects: {hunger: -15}
          narrative: "{caller}拈了几颗花生丢进嘴里，咸香脆口\"""")
    pdf.body("-> Python 代码零改动。LLM 自动在 prompt 中看到花生，Agent 饿了自己会去吃。")

    pdf.h2("例子 2: 加一个新 NPC (希里)")
    pdf.code_block("""- id: ciri
  name: "希里"
  zone: square
  pos: [9, 6]
  visual: {...}
  interaction:
    actions:
      交谈: {target_type: agent}
      切磋: {target_type: passive, resolve: llm}
  agent:
    autonomous: true
    personality: "辛特拉幼狮，正在躲避狂猎的追捕..."
    drives:
      hunger: {decay: 0.02}
      thirst: {decay: 0.025}""")

    pdf.h2("例子 3: 加一个新 zone (凯尔莫罕)")
    pdf.code_block("""zones:
  - id: kaer_morhen
    name: "凯尔莫罕"
    width: 20
    height: 14
  # + connections + gate entities + 实体

-> Python 代码零改动。前端加载时自动渲染。""")

    pdf.h1("Godot 前端计划")
    pdf.body("当前前端用 Phaser.js (网页)。计划升级到 Godot 4.x 游戏引擎。后端一行不改。")
    pdf.body("升级后的提升：")
    pdf.bullet("真正的像素精灵动画（走路 4 方向 × 4 帧）")
    pdf.bullet("碰撞检测（不会穿过墙）")
    pdf.bullet("Tiled 编辑器直接编辑瓦片地图（不用手写坐标）")
    pdf.bullet("导出 Windows/Mac/Linux 桌面应用 + 浏览器")
    pdf.bullet("原生音频系统 + 粒子特效")
    pdf.body("改动范围：只替换 web/ 目录。src/ 和 config/ 全部不变。")

    pdf.h1("技术要点速查")
    pdf.table(
        ["指标", "数值"],
        [
            ["源文件", "27 个 .py + 3 个 .yaml + 6 个 web/"],
            ["LLM 调用点", "2 个 (决策 + 裁判)"],
            ["Agent 循环", "while alive: decay -> sense -> think -> move -> interact -> sleep"],
            ["交互模式", "3 种 (rule引擎 / llm裁判 / inbox消息)"],
            ["API 端点", "8 个 REST + 1 个 WebSocket"],
            ["测试规模", "3 zones × 23 entities × 3 NPCs, 21/21 属性合规"],
            ["扩展方式", "只改 YAML, 不改 Python"],
        ],
        [40, 158]
    )

    return pdf


# =======================================
# Main
# =======================================

if __name__ == "__main__":
    print("Generating professional PDF...")
    prof = build_professional()
    prof.output(os.path.join(OUT_DIR, "AgentWorld_Async_Technical.pdf"))
    print(f"  -> {OUT_DIR}/AgentWorld_Async_Technical.pdf ({prof.pages_count} pages)")

    print("Generating plain language PDF...")
    plain = build_plain()
    plain.output(os.path.join(OUT_DIR, "AgentWorld_Async_Plain.pdf"))
    print(f"  -> {OUT_DIR}/AgentWorld_Async_Plain.pdf ({plain.pages_count} pages)")
    print("Done.")
