#!/usr/bin/env python3
"""Generate external agent issues analysis PDF."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from fpdf import FPDF

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
os.makedirs(OUT_DIR, exist_ok=True)

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
for root, _, files in os.walk("/usr/share/fonts"):
    for f in files:
        if "NotoSansCJK" in f and "Regular" in f:
            FONT_PATH = os.path.join(root, f); break

class IssuePDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        bold = FONT_PATH.replace("Regular","Bold")
        self.add_font("CN", "", FONT_PATH)
        self.add_font("CN", "B", bold if os.path.exists(bold) else FONT_PATH)
        self.set_auto_page_break(True, 12)
        self.add_page()

    def header(self):
        if self.page_no() == 1:
            self.set_font("CN", "B", 18)
            self.cell(0, 11, "外部 Agent 接入 — 潜在问题分析", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("CN", "", 9)
            self.set_text_color(100)
            self.cell(0, 6, "External Agent Integration — Risk & Issue Analysis", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0)
            self.line(self.l_margin, self.y+2, self.w-self.r_margin, self.y+2)
            self.ln(8)
        else:
            self.set_font("CN", "", 7)
            self.set_text_color(128)
            self.cell(0, 5, "外部Agent接入问题分析", align="L")
            self.cell(0, 5, f"p.{self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0)

    def severity(self, level):
        colors = {"P0":(180,30,30),"P1":(200,120,0),"P2":(60,60,160)}
        c = colors.get(level,(0,0,0))
        self.set_font("CN","B",14)
        self.set_text_color(*c)
        w = self.get_string_width(level)+4
        self.cell(w, 8, level, align="C")
        self.set_text_color(0)
        return w

    def issue(self, num, title, sev):
        self.ln(3)
        w = self.severity(sev)
        self.set_font("CN","B",12)
        self.cell(0, 7, f"#{num}  {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*(180,30,30) if sev=="P0" else (200,120,0) if sev=="P1" else (60,60,160))
        self.set_line_width(0.4)
        self.line(self.l_margin, self.y, self.w-self.r_margin, self.y)
        self.ln(2)

    def field(self, label, text):
        self.set_font("CN","B",8.5)
        self.set_fill_color(245,245,250)
        w = self.get_string_width(label+"  ")+4
        self.cell(w, 6.5, f"  {label}", fill=True)
        self.set_font("CN","",8.5)
        self.set_x(self.l_margin+w+2)
        self.multi_cell(self.w-self.l_margin-w-self.r_margin-2, 6.5, text)
        self.ln(1)

    def code(self, text):
        self.ln(1)
        self.set_font("CN","",7)
        self.set_fill_color(250,250,255)
        for line in text.strip().split("\n"):
            self.cell(self.w-2*self.l_margin, 4.3, "  "+line[:125], fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def fix(self, text):
        self.set_font("CN","",8.5)
        self.set_fill_color(230,255,230)
        self.cell(14, 6, "  修复:", fill=True)
        self.set_x(self.l_margin+14)
        self.multi_cell(self.w-self.l_margin-self.r_margin-14, 6, text)
        self.ln(1)

    def table(self, headers, rows, widths):
        total=sum(widths)
        if total>self.w-2*self.l_margin:
            scale=(self.w-2*self.l_margin)/total
            widths=[w*scale for w in widths]
        self.set_font("CN","B",7.5)
        self.set_fill_color(50,50,80); self.set_text_color(255,255,255)
        for i,h in enumerate(headers): self.cell(widths[i],6,h,border=1,fill=True,align='C')
        self.ln(); self.set_text_color(0)
        self.set_font("CN","",7.5)
        for ri,row in enumerate(rows):
            self.set_fill_color(248,248,252) if ri%2==0 else self.set_fill_color(255,255,255)
            for i,c in enumerate(row): self.cell(widths[i],5.5,str(c)[:80],border=1,fill=True,align='C')
            self.ln()
        self.set_x(self.l_margin); self.ln(2)


def build():
    pdf = IssuePDF()

    pdf.set_font("CN","",9)
    pdf.multi_cell(0,5.5,
        "外部 Agent 通过 REST + WebSocket 接入 AgentWorld Async 时，"
        "当前实现存在 11 个潜在问题。按严重度 P0(立即)/P1(高)/P2(中)分级。"
        "每个问题包含: 根因、当前表现、影响范围、修复方案。")
    pdf.ln(3)

    # ── Summary table ──
    pdf.set_font("CN","B",11)
    pdf.cell(0,7,"问题总览",new_x="LMARGIN",new_y="NEXT")
    pdf.ln(2)
    pdf.table(
        ["#","严重度","问题","影响","修复工作量"],
        [
            ["1","P0","断线后Entity残留","僵尸污染世界","~15行"],
            ["2","P0","Busy时可移动","逻辑断裂","~5行"],
            ["3","P0","不校验Zone边界","走到地图外","~10行"],
            ["4","P0","交互轮询阻塞WS","15秒不可收消息","~20行"],
            ["5","P0","重复连接不一致","重复Entity","~15行"],
            ["6","P1","跨Zone不更新Grid","换Zone后隐身","~10行"],
            ["7","P1","无心跳检测","死连接堆积","~20行"],
            ["8","P1","Inbox从不读取","收不到他人消息","~20行"],
            ["9","P1","无安全机制","任意注册/冒充","~30行"],
            ["10","P2","属性不可配置","coin固定20","~10行"],
            ["11","P2","请求无校验","无效action不拦截","~15行"],
        ],
        [8,16,36,40,30]
    )
    pdf.ln(2)

    # ═══════════════════════════════════
    # P0 issues
    # ═══════════════════════════════════
    pdf.issue(1,"断线后 Entity 僵尸残留 — 未清理 world.entities 和 SpatialGrid","P0")
    pdf.field("当前表现",
        "外部 agent 的 WebSocket 断开(正常关闭或网络断开)。WS disconnect handler 只从 ConnectionManager 移除，"
        "未从 world.entities 字典中删除 Entity 对象, 未从 spatial_grid 中移除坐标。")
    pdf.field("根因",
        "World 没有 `unregister_entity()` 方法。send_tg/disconnect handler 只调了 ConnectionManager.unregister_agent。")
    pdf.field("影响",
        "僵尸 Entity 永久留在世界中。其他 agent 的 SensorySystem 能看到它。"
        "5分钟断线接入后,世界里有 5 个不动的死人。SpatialGrid 被污染, query 返回不存在的 ID。")
    pdf.code("""
# 当前: WS disconnect 清理不完整
except WebSocketDisconnect:
    pass                       # 什么都没做
finally:
    await manager.unregister_agent(agent_id)  # 只清理WS,不清Entity""")
    pdf.fix("World.unregister_entity(id): 从 entities dict 删除 + 从 grid remove。WS disconnect 时调用。")

    pdf.issue(2,"外部 Agent busy 时仍可移动","P0")
    pdf.field("当前表现","外部 agent 提交了'饮用'交互, status=busy。此时客户端发 move 消息, _handle_move 直接执行, 没有检查 status。")
    pdf.field("根因","_handle_move() 没有检查 self.entity.status, 而 Entity.move_to 也没有内部检查。")
    pdf.field("影响","外部 agent 可以一边喝麦酒一边瞬移。逻辑断裂: busy 状态的'不能同时做新动作'被绕过。")
    pdf.code("""
async def _handle_move(self, msg):
    to = msg.get("to")
    self.entity.move_to(to)  # 没有检查 status != idle""")
    pdf.fix("_handle_move 开头加 if self.entity.status != 'idle': return error。_handle_interact 也要加。")


    pdf.issue(3,"移动不校验 Zone 边界","P0")
    pdf.field("当前表现","客户端发送 move {to: [999,999]}。Entity.move_to 直接执行, 不检查 zone.width/height 上限。")
    pdf.field("根因","Entity.move_to 只做距离计算, 没有 zone 边界信息。调用方(_handle_move)没传 zone 元数据。")
    pdf.field("影响","外部 agent 走到坐标[999,999], SensorySystem.update 在 spatial_grid 里找不到它的 cell, query 抛索引越界。物理上 agent 永久'脱离'世界。")
    pdf.code("""
# 修复: move 前校验
zone = self.world.zones[self.entity.zone]
if not (0 <= to[0] < zone["width"] and 0 <= to[1] < zone["height"]):
    return error("out of bounds")""")

    pdf.issue(4,"交互结果轮询阻塞 WS 消息处理","P0")
    pdf.field("当前表现","外部 agent 提交交互后, _handle_interact 进入 30 次 x0.5s=15s 的轮询等待。期间 WS 的 handle_message 被困在这个循环里, 无法处理客户端发来的其他消息(sensory请求/move)。")
    pdf.field("根因","用了 sleep+check 轮询而非 asyncio.Event 通知。_handle_interact 是 handle_message 的同步调用, 轮询期间 WS receive loop 被阻塞。")
    pdf.field("影响","外部 agent 在等待交互结果期间完全失联。无法拉取最新 sensory, 无法取消交互。客户端 15 秒超时。")
    pdf.code("""
# 当前: 轮询 15s
for _ in range(30):
    await asyncio.sleep(0.5)
    if self.entity.busy_result is not None: ...

# 修复: Event 通知
self.entity.busy_event = asyncio.Event()
await self.entity.busy_event.wait()  # 零轮询""")

    pdf.issue(5,"同一 agent_id 重复连接处理不一致","P0")
    pdf.field("当前表现","REST POST /agents 检测 id 已存在时返回 HTTP 400。WebSocket /ws/agent/{id} 连接时如果 id 已存在且 WS 未注册到 ConnectionManager, 会尝试 register_external_agent, 导致冲突。")
    pdf.field("根因","REST 和 WS 两套注册逻辑不一致。WS 没有断线清理, 也没有重连复用。")
    pdf.field("影响","外部 agent 断线重连后: WS 是新连接, Entity 是旧的。sensory 是旧的, status 可能是 busy。或者 REST 直接拒绝, 客户端无法重连。")
    pdf.fix("统一: 重连时复用现有 Entity(reset status+sensory), 不创建新 Entity。加上 disconnect 时标记 entity.inactive 而非删除, 给 reconnect 留一个窗口。")


    # ═══════════════════════════════════
    # P1 issues
    # ═══════════════════════════════════
    pdf.issue(6,"跨 Zone 移动不更新 SpatialGrid","P1")
    pdf.field("当前表现","外部 agent 走 gate 进入酒馆。apply_result 设置 agent.zone='bar_zone', agent.pos=[1,4]。但 square 的 spatial_grid 仍包含该 entity, bar_zone 的 grid 没有。")
    pdf.field("根因","apply_result 处理 zone 迁移时只改了 agent.zone 和 agent.pos, 没有调用 world.notify_moved 做跨 zone 的 grid 迁移。grid.move 只处理同 zone 内移动。")
    pdf.field("影响","外部 agent 换 zone 后在新 zone 的 SensorySystem 扫不到它(query 旧 zone 的 grid 返回它, 但 entity.zone 已经是新 zone 了, 被过滤掉)。agent 在新 zone 里'隐身'。")
    pdf.fix("World.notify_zone_changed(entity, old_zone, new_zone, old_pos, new_pos): 从旧 grid remove, 新 grid insert。在 apply_result 处理 zone 迁移后调用。")


    pdf.issue(7,"无心跳检测 — 死连接堆积","P1")
    pdf.field("当前表现","TCP 半开连接(网络断开但 WS 未收到 close frame)。服务端认为外部 agent 仍在连接。websockets 库有内置 ping/pong, 但超时踢人未配置。")
    pdf.field("根因","WebSocket 协议有 ping/pong 机制, 但 uvicorn/websockets 的默认超时可能很长(数分钟)。没有应用层心跳或显式超时。")
    pdf.field("影响","网络抖动后, 服务端保留死连接数分钟。此期间外部 agent 接收不到消息, 但 native agent 可见它的 Entity。同时多个死连接后, WS 广播推送给死连接会超时, 拖慢整体推送。")
    pdf.fix("uvicorn 配置 ws_ping_interval=15 + ws_ping_timeout=10。超时未收到 pong → 触发 disconnect → 清理 Entity。")


    pdf.issue(8,"外部 Agent 的 Inbox 从不读取","P1")
    pdf.field("当前表现","杰洛特向特莉丝(外部 agent)发 inbox 消息。消息写入特莉丝的 inbox.messages。但 ExternalAgentProxy 的主循环不 drain inbox。消息永久堆积。")
    pdf.field("根因","ExternalAgentProxy.handle_message 只处理 move/interact/sensory/command 四种消息类型。没有 'drain_inbox' 或 'check_messages'。")
    pdf.field("影响","外部 agent 完全不知道有 NPC 跟它说话。杰洛特发了消息以为对方会回, 实际石沉大海。双向互动断裂。")
    pdf.fix("两种方案: (A) 外部 agent 主动 POST /agents/{id}/sensory 时, 返回数据中包含 inbox_messages; (B) WS 主动 push inbox_messages 给外部 agent。方案 A 更简单。")


    pdf.issue(9,"无安全机制","P1")
    pdf.field("当前表现","任何人可以 POST /api/v1/agents 注册。任何人可以 GET /api/v1/world/state 获取全量数据。无 token 验证, 无 rate limit。")
    pdf.field("根因","设计时聚焦功能验证, 安全是事后考虑。CORS 已开放 *。")
    pdf.field("影响","恶意方可以: (1) 注册 1000 个 agent 耗尽内存 (2) 频繁 move/interact 触发 LLM 调用消耗 API 配额 (3) 读取完整世界状态窃取设计数据。")
    pdf.fix("1. API token 中间件(简单 bearer token)。2. 注册 agent 需要提供 token。3. 每 token 限制 agent 数(如 3 个)。4. Rate limit (如 10 次/秒)。不需要完整的 OAuth。")


    # ═══════════════════════════════════
    # P2 issues
    # ═══════════════════════════════════
    pdf.issue(10,"外部 Agent 属性不可配置","P2")
    pdf.field("当前表现","register_external_agent 写死: coins=20, mood=60, interaction_radius=3。外部 agent 注册时传的 personality 参数只影响视觉层描述, 不影响属性。")
    pdf.field("根因","register_external_agent 的签名只有 agent_id/name/zone/pos/sprite/personality, 没有 private_attrs 或 interaction_radius 参数。")
    pdf.field("影响","外部 agent 无法自定义初始属性(如特莉丝带 500 金币)。所有外部 agent 看起来一模一样。")
    pdf.fix("register_external_agent 增加 private_attrs 可选参数。如果传入, 覆盖默认。routes.py 和 ws handler 传递客户端配置。")


    pdf.issue(11,"请求无业务校验","P2")
    pdf.field("当前表现","交互请求 {target_entity:'notice_board', action:'饮用'} 可以提交(公告板没有'饮用'动作)。_handle_interact 只检查 target 存在和 can_interact, 不检查 action 是否是 target 的有效动作。")
    pdf.field("根因","InteractionSystem.submit 检查 action 是否存在(act_def is not None), 如果不存在会抛 ValueError。但 external.py 虽然有 try/except, 客户端收到的错误信息不够明确。")
    pdf.field("影响","客户端发错 action 时得到通用错误, 调试困难。本应在提交前做一次 action 存在性校验, 返回友好提示。")
    pdf.fix("_handle_interact 开头加: 检查 target.get('interaction').get_action(action) 是否存在。不存在返回 {error:'action not available', available:[...]}")


    # ── Priority matrix ──
    pdf.ln(5)
    pdf.set_font("CN","B",13)
    pdf.cell(0,8,"修复优先级矩阵",new_x="LMARGIN",new_y="NEXT")
    pdf.ln(3)
    pdf.table(
        ["顺序","#","问题","工作量","修复后效果"],
        [
            ["①","1","断线Entity残留","15行","僵尸不再污染世界"],
            ["②","2","Busy可移动","5行","外部agent不能瞬移"],
            ["③","3","Zone边界","10行","走不到地图外"],
            ["④","5","重复连接","15行","断线重连正常"],
            ["⑤","4","轮询阻塞","20行","交互期间仍可控"],
            ["⑥","6","Zone迁移Grid","10行","换Zone不隐身"],
            ["⑦","8","Inbox读取","20行","能收到NPC消息"],
            ["⑧","7","心跳检测","20行","死连接自动清理"],
            ["⑨","9","安全机制","30行","token+rate limit"],
            ["⑩","10","属性可配","10行","自定义初始属性"],
            ["⑪","11","请求校验","15行","友好错误提示"],
        ],
        [12,8,36,20,54]
    )

    pdf.ln(3)
    pdf.set_font("CN","",9)
    pdf.multi_cell(0,5.5,
        "P0 共 5 个问题, 累计修改 ~65 行。修复后外部 agent 连接/断开/移动/交互/重连的基础稳定性达到可用水平。"
        "P1 共 4 个问题, 累计修改 ~80 行。修复后生产环境安全和运维能力具备。"
        "P2 共 2 个问题, 累计修改 ~25 行。修复后用户体验完善。")

    path = os.path.join(OUT_DIR, "AgentWorld_Async_ExternalAgent_Issues.pdf")
    pdf.output(path)
    return path

if __name__ == "__main__":
    path = build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
