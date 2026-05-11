#!/usr/bin/env python3
"""Generate bottleneck analysis PDF."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from fpdf import FPDF

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
os.makedirs(OUT_DIR, exist_ok=True)

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if not os.path.exists(FONT_PATH):
    for root, _, files in os.walk("/usr/share/fonts"):
        for f in files:
            if "NotoSansCJK" in f and "Regular" in f:
                FONT_PATH = os.path.join(root, f); break

class BottleneckPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.add_font("CN", "", FONT_PATH)
        bold = FONT_PATH.replace("Regular", "Bold")
        if os.path.exists(bold):
            self.add_font("CN", "B", bold)
        else:
            self.add_font("CN", "B", FONT_PATH)
        self.set_auto_page_break(True, 12)
        self.add_page()

    def header(self):
        if self.page_no() == 1:
            self.set_font("CN", "B", 20)
            self.cell(0, 12, "AgentWorld Async — 规模化瓶颈分析", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("CN", "", 9)
            self.set_text_color(100)
            self.cell(0, 6, "Scaling Bottleneck Analysis", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0)
            self.line(self.l_margin, self.y+2, self.w-self.r_margin, self.y+2)
            self.ln(8)
        else:
            self.set_font("CN", "", 7)
            self.set_text_color(128)
            self.cell(0, 5, "规模化瓶颈分析", align="L")
            self.cell(0, 5, f"p.{self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0)

    def section(self, num, title, severity):
        colors = {"P0": (180,30,30), "P1": (200,120,0), "P2": (60,60,160), "P3": (80,80,80)}
        c = colors.get(severity, (0,0,0))
        self.ln(3)
        self.set_font("CN", "B", 14)
        self.set_text_color(*c)
        self.cell(12, 8, f"#{num}", align="L")
        self.set_text_color(0)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*c)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.y, self.w-self.r_margin, self.y)
        self.ln(3)

    def field(self, label, text):
        self.set_font("CN", "B", 9)
        self.set_fill_color(245, 245, 250)
        w = self.get_string_width(label + "  ") + 4
        self.cell(w, 7, f"  {label}", fill=True)
        self.set_font("CN", "", 9)
        self.set_x(self.l_margin + w + 2)
        self.multi_cell(self.w - self.l_margin - w - self.r_margin - 2, 7, text)
        self.ln(1)

    def code(self, text):
        self.ln(1)
        self.set_font("CN", "", 7)
        self.set_fill_color(250, 250, 255)
        for line in text.strip().split("\n"):
            self.cell(self.w - 2*self.l_margin, 4.5, "  " + line[:125], fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def table(self, headers, rows, widths):
        total = sum(widths)
        if total > self.w - 2*self.l_margin:
            scale = (self.w - 2*self.l_margin) / total
            widths = [w*scale for w in widths]
        self.set_font("CN", "B", 7.5)
        self.set_fill_color(50,50,80)
        self.set_text_color(255,255,255)
        for i,h in enumerate(headers):
            self.cell(widths[i], 6, h, border=1, fill=True, align='C')
        self.ln()
        self.set_text_color(0)
        self.set_font("CN", "", 7.5)
        for ri, row in enumerate(rows):
            if ri % 2 == 0: self.set_fill_color(248,248,252)
            else: self.set_fill_color(255,255,255)
            for i,c in enumerate(row):
                self.cell(widths[i], 5.5, str(c)[:80], border=1, fill=True, align='C')
            self.ln()
        self.set_x(self.l_margin)
        self.ln(2)


def build():
    pdf = BottleneckPDF()

    # ── Intro ──
    pdf.set_font("CN", "", 9)
    pdf.multi_cell(0, 5.5,
        "本文档分析 AgentWorld Async 在从单 Agent Demo 扩展到多 Agent 生产环境时可能遇到的 8 个架构瓶颈。"
        "每个瓶颈包含：触发条件、根因、解决方案、通俗解释。严重度 P0 = 最紧急，P3 = 最缓。")
    pdf.ln(4)

    # ── Threshold table ──
    pdf.set_font("CN", "B", 11)
    pdf.cell(0, 7, "整体阈值估计", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.table(
        ["Agent 数", "Entity 数", "触发瓶颈", "表现"],
        [
            ["1-5", "<100", "无", "流畅, ~2s/轮"],
            ["10-20", "<500", "#1 LLM线程池, #3 轮询", "每轮间隔 2s->6s"],
            ["50-100", "<2000", "#2 扫描O(n*m), #4 Inbox洪水", "Agent反应越来越慢"],
            ["200+", "<5000", "全部瓶颈同时", "不可用"],
        ],
        [32, 32, 62, 62]
    )

    # ═══════════════════════════════════
    # Bottleneck 1
    # ═══════════════════════════════════
    pdf.section(1, "LLM 调用 — 线程池饱和", "P0")
    pdf.field("瓶颈点", "LLMClient 的 ThreadPoolExecutor(max_workers=4) 是所有 LLM 调用的唯一通道")
    pdf.field("触发条件", "Agent 数 > 线程池大小 (4)。每个 Agent 每轮至少 1 次 LLM 调用 (think)。交互时额外 1 次 LLM 调用 (resolve)")
    pdf.field("根因", "每个 Agent 独立调 LLM，无法批量。4 个线程处理 N 个请求，排队时间随 N 线性增长")
    pdf.field("解决方案",
        "Combined Prompt: 将多个 Agent 的决策合并为一次 LLM 调用。v1 已使用此技术 (_build_combined_prompt)。"
        "或增加线程池大小 (短期缓解)")
    pdf.field("通俗解释",
        "4 个收银台，10 个人排队结账。前 4 个人 2 秒结完，第 5-8 再等 2 秒，第 9-10 又等 2 秒。"
        "人越多越慢。解决办法：一个人帮大家集体结账。")
    pdf.code("""
# 当前: 每个 Agent 单独调
for agent in agents:
    decision = await brain.decide(context)  # 1 次 LLM 调用

# 优化后: 合并 prompt
combined = build_combined_prompt(all_contexts)
results = await llm.chat(combined)          # 1 次 LLM 调用
decisions = parse_combined_results(results)""")

    # ═══════════════════════════════════
    # Bottleneck 2
    # ═══════════════════════════════════
    pdf.section(2, "SensorySystem — O(n×m) 全量扫描", "P0")
    pdf.field("瓶颈点", "SensorySystem.update() 对每个 observer 遍历 all_entities")
    pdf.field("触发条件", "Agent × Entity > 10,000。例如 100 Agent × 1000 Entity = 100,000 次距离计算/轮")
    pdf.field("根因", "无空间索引。同一 zone 内的实体也要逐一计算距离，而不是只算附近的")
    pdf.field("解决方案",
        "空间哈希/网格索引: 按 tile 坐标分组 (如每 5×5 一格)。SensorySystem 只检查 observer 所在格及邻格的实体。复杂度从 O(n×m) 降到 O(n×k)，k 为邻格实体数 (<50)。")
    pdf.field("通俗解释",
        "你在 40×30 的大广场上，想知道周围有没有人。现在做法是把广场上每个人都量一遍距离。"
        "优化后：把广场分成 5×5 的格子，你只看自己格子 + 周围 8 个格子里的人。")
    pdf.code("""
# 当前: 全量扫描
for entity in all_entities.values():  # m 个实体
    if entity.zone != observer.zone: continue
    d = observer.distance_to(entity)  # 每个都算距离

# 优化后: 空间哈希
grid = SpatialGrid(tile_size=5)
for entity in all_entities.values():
    grid.insert(entity)  # O(1)

# 查询时只看附近格子
nearby = grid.query(observer.pos, radius=observer.view_radius)
# 只对 nearby (<50个) 做距离计算""")

    # ═══════════════════════════════════
    # Bottleneck 3
    # ═══════════════════════════════════
    pdf.section(3, "Busy Loop — 轮询等结果", "P1")
    pdf.field("瓶颈点", "Agent busy 时每秒醒来检查 busy_result 是否到达，空转浪费")
    pdf.field("触发条件", "Agent 频繁进入 busy 状态 (每次 LLM resolve 需 3-8 秒)。多个 Agent 同时 busy 时每秒多次无效检查")
    pdf.field("根因", "当前用轮询模式: agent sleeps → wakes → checks → sleeps again。没有通知机制")
    pdf.field("解决方案",
        "asyncio.Event 模式: Resolver 完成后 event.set()，Agent await event.wait()。零轮询。"
        "或直接 await 后台 task (但当前 task 是 fire-and-forget)")
    pdf.field("通俗解释",
        "你点了外卖，每秒查一次手机看快递到哪了。改成：外卖到了给你发个通知，你收到通知再去看。")
    pdf.code("""
# 当前: 轮询
if agent.busy_result is not None:
    apply(result)
await asyncio.sleep(1.0)  # 每秒检查一次

# 优化后: Event 通知
agent.busy_event = asyncio.Event()
# ... Resolver 完成后:
agent.busy_result = result
agent.busy_event.set()     # 通知 Agent

# Agent 端:
await agent.busy_event.wait()  # 阻塞等待，零 CPU
apply(agent.busy_result)""")

    # ═══════════════════════════════════
    # Bottleneck 4
    # ═══════════════════════════════════
    pdf.section(4, "Inbox — Agent 间消息无节流", "P1")
    pdf.field("瓶颈点", "每个 Agent 每轮 drain inbox，消息列表无限增长注入 LLM prompt")
    pdf.field("触发条件", "Agent 数 > 20 时互相发消息。每轮 inbox 可能有几十条。LLM prompt token 数爆炸")
    pdf.field("根因", "无消息过滤或摘要机制。全部消息原样注入 prompt")
    pdf.field("解决方案",
        "消息摘要 + 优先级: 只注入最重要的 N 条 (最近 + 来自重要 NPC 的)。其余合并为 '还有 X 个人跟你说了话'。"
        "重要性由 social 驱动力权重决定")
    pdf.field("通俗解释",
        "你一天收到 50 条微信，不可能每条都看。看最上面 5 条，下面的扫一眼标题。"
        "你的 AI 大脑也是，只给它看最重要的几条，剩下的总结成一句话。")
    pdf.code("""
# 优化后: 消息摘要
def summarize_messages(msgs, max_display=5):
    important = sorted(msgs, key=lambda m: m.importance, reverse=True)
    result = important[:max_display]
    remaining = len(msgs) - max_display
    if remaining > 0:
        result.append(Message(summary=f"还有 {remaining} 条未读消息"))
    return result""")

    # ═══════════════════════════════════
    # Bottleneck 5
    # ═══════════════════════════════════
    pdf.section(5, "Resolver 无缓存 — 相似交互重复裁定", "P2")
    pdf.field("瓶颈点", "每次 resolve=llm 的交互都调 LLM #2，即使和前次的裁定逻辑几乎相同")
    pdf.field("触发条件", "同类型交互高频重复 (如多个 Agent 各喝多杯酒)。每次 LLM 调用 ~2-3 秒")
    pdf.field("根因", "resolve=llm 没有缓存或去重。杰洛特喝第1杯 vs 第3杯的裁定逻辑几乎一样，但各调一次 LLM")
    pdf.field("解决方案",
        "① resolve=rule 化: 把频繁的简单交互(喝水/坐/捡)改成 rule 模式。"
        "② 缓存相似裁定: 同实体+同动作+状态窗口内 → 复用上次结果。"
        "③ LLM #2 只在社交/复杂场景调用")
    pdf.field("通俗解释",
        "去便利店买水不用跟老板讨价还价，扫码付钱就行。但买古董要谈。"
        "项目里：喝水 = 便利店 (rule 直接算)，跟老板聊天 = 买古董 (LLM 来谈)。")
    pdf.code("""
# 当前: 喝麦酒走 LLM
actions:
  饮用:
    resolve: llm          # 每次调 LLM

# 优化: 改为 rule
actions:
  饮用:
    resolve: rule
    rule:
      cost: {coins: -5}
      effects: {thirst: -25}
      narrative: "{caller}喝下一杯麦酒，畅快解渴"

# 搭话/讨价还价保留 llm""")

    # ═══════════════════════════════════
    # Bottleneck 6
    # ═══════════════════════════════════
    pdf.section(6, "EventEntity — 泄露与命名冲突", "P2")
    pdf.field("瓶颈点", "事件实体被加入 world.entities，SensorySystem 扫描时一并处理。过期删除靠定期 prune")
    pdf.field("触发条件", "高交互频率 > 10 次/秒。3 分钟窗口内堆积大量过期未删事件实体。UUID 8 位碰撞概率上升")
    pdf.field("根因", "事件实体和持久实体混在同一个 dict。prune 遍历全部事件实体而非按时间索引")
    pdf.field("解决方案",
        "事件实体不进 world.entities，进独立事件队列。按过期时间维护优先级队列，prune 只查队头。"
        "SensorySystem 从事件队列取当前 zone 的事件。UUID 改 12 位")
    pdf.field("通俗解释",
        "快递包裹和家里家具堆在一起。每次打扫卫生要把所有东西翻一遍看看哪些快递过期了。"
        "优化后：快递放门口专门架子上，按过期时间排，只看最前面那个。")
    pdf.code("""
# 当前: 混合存储
world.entities[event.id] = event       # 混在一起
# prune 遍历全部
for eid, evt in world.active_events:   # O(n)

# 优化后: 分离存储 + 堆
import heapq
event_heap = []                         # 按过期时间的最小堆
heapq.heappush(event_heap, (expire_at, event))
# prune 只查队头
while event_heap and event_heap[0][0] < now:
    heapq.heappop(event_heap)           # O(log n)""")

    # ═══════════════════════════════════
    # Bottleneck 7
    # ═══════════════════════════════════
    pdf.section(7, "WebSocket 广播 — 串行推送", "P2")
    pdf.field("瓶颈点", "broadcast_to_frontend() 循环 await ws.send_json()，串行推送")
    pdf.field("触发条件", "前端观察者 > 10。每个事件推 N 次，串行 await 导致前一个慢连接阻塞后面所有")
    pdf.field("根因", "for ws in clients: await ws.send() — 串行。一个慢客户端拖慢整批推送")
    pdf.field("解决方案",
        "asyncio.gather() 并发推送。或使用 Redis PubSub 做消息中间件，后端只 publish，前端各自 subscribe")
    pdf.field("通俗解释",
        "老师发卷子，一个一个走到座位前发。50 个人等着。优化后：把卷子交给每组组长，同时发。")
    pdf.code("""
# 当前: 串行
for ws in clients:
    await ws.send_json(data)  # 前面卡了后面全等

# 优化后: 并发
tasks = [ws.send_json(data) for ws in clients]
await asyncio.gather(*tasks, return_exceptions=True)""")

    # ═══════════════════════════════════
    # Bottleneck 8
    # ═══════════════════════════════════
    pdf.section(8, "DriveSystem + private_attrs 属性共享字典", "P3")
    pdf.field("瓶颈点", "DriveSystem.attrs 和 InteractionLayer.private_attrs 是同一个 dict 引用。已修复")
    pdf.field("触发条件", "多个 System 同时修改属性时可能产生竞争。当前单 asyncio 线程无此问题")
    pdf.field("根因", "Python dict 在单线程下安全。多线程时需要加锁保护属性读写")
    pdf.field("解决方案", "当前无问题。未来如果引入多线程模型 (如 LLM 调用放线程池)，需要加 threading.Lock")
    pdf.field("通俗解释", "当前只有一个收银员，不存在两个人同时收钱的问题。以后开多个收银台了才需要排队。")

    # ── Summary ──
    pdf.ln(5)
    pdf.set_font("CN", "B", 13)
    pdf.cell(0, 8, "优先级汇总", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.table(
        ["#", "瓶颈", "严重度", "现状", "优化方案", "改造成本"],
        [
            ["1", "LLM 线程池饱和", "P0", "4 线程", "Combined Prompt 批量调用", "低 (~100行)"],
            ["2", "SensorySystem O(n*m)", "P0", "全量扫描", "空间哈希/网格索引", "中 (~200行)"],
            ["3", "Busy Loop 轮询", "P1", "sleep+check", "asyncio.Event 通知", "低 (~30行)"],
            ["4", "Inbox 消息洪水", "P1", "无节流", "消息摘要+优先级", "低 (~50行)"],
            ["5", "Resolver 无缓存", "P2", "每次调LLM", "rule化+缓存", "低 (改YAML)"],
            ["6", "EventEntity 泄露", "P2", "混合存储", "独立队列+堆", "中 (~150行)"],
            ["7", "WS 广播串行", "P2", "串行await", "asyncio.gather", "低 (~10行)"],
            ["8", "属性共享线程安全", "P3", "单线程OK", "Lock (if needed)", "极低"],
        ],
        [8, 42, 18, 28, 52, 40]
    )
    pdf.ln(2)
    pdf.set_font("CN", "", 9)
    pdf.multi_cell(0, 5.5,
        "结论: 当前 1-3 Agent 规模下无瓶颈。前 4 项 (P0-P1) 应在 Agent 数超过 10 前优化。"
        "P0 项的 Combined Prompt 是 v1 已验证的成熟技术，可直接移植。P2 项可在 Agent 50+ 时处理。")

    # ── Output ──
    path = os.path.join(OUT_DIR, "AgentWorld_Async_Bottleneck_Analysis.pdf")
    pdf.output(path)
    return path

if __name__ == "__main__":
    path = build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
