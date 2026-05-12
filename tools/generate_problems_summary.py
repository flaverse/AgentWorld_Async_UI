#!/usr/bin/env python3
"""Generate Problems & Fixes PDF — Bilingual EN+CN."""
import os,sys
from fpdf import FPDF

OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','docs','AgentWorld_Async_Problems_and_Fixes.pdf')
os.makedirs(os.path.dirname(OUT),exist_ok=True)

FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
for r,d,files in os.walk('/usr/share/fonts'):
    for f in files:
        if 'NotoSansCJK' in f and 'Regular' in f: FONT=os.path.join(r,f); break

class PDF(FPDF):
    def __init__(self,t):
        super().__init__('P','mm','A4')
        self.t=t
        bold=FONT.replace('Regular','Bold')
        self.add_font('C','',FONT)
        self.add_font('C','B',bold if os.path.exists(bold) else FONT)
        self.set_auto_page_break(True,10)
        self.add_page()
    def header(self):
        if self.page_no()>1:
            self.set_font('C','',6); self.set_text_color(128)
            self.cell(0,5,self.t,align='L')
            self.cell(0,5,f'p.{self.page_no()}',align='R',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0)
        else:
            self.set_font('C','B',16)
            self.cell(0,9,self.t,align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_font('C','',8); self.set_text_color(100)
            self.cell(0,5,'Bilingual — 中英双语',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0); self.ln(5)
    def h1(self,cn,en):
        self.ln(2); self.set_font('C','B',13)
        self.cell(0,7,f'{cn}  ({en})',new_x='LMARGIN',new_y='NEXT')
        self.set_draw_color(60,60,160); self.line(self.l_margin,self.y,self.w-self.r_margin,self.y); self.ln(2)
    def h2(self,cn,en):
        self.ln(1); self.set_font('C','B',10)
        self.cell(0,6,f'{cn} ({en})',new_x='LMARGIN',new_y='NEXT'); self.ln(1)
    def b(self,cn,en=''):
        self.set_x(self.l_margin)
        self.set_font('C','',8.5)
        self.multi_cell(0,4.5,cn)
        if en:
            self.set_x(self.l_margin)
            self.set_font('C','',7.5); self.set_text_color(100)
            self.multi_cell(0,4,en)
            self.set_text_color(0)
        self.ln(1)
    def bl(self,cn,en=''):
        self.set_font('C','',8.5); self.cell(self.w-2*self.l_margin,5,'  - '+cn,new_x='LMARGIN',new_y='NEXT')
        if en:
            self.set_font('C','',7.5); self.set_text_color(100)
            self.set_x(self.l_margin+8)
            self.cell(self.w-2*self.l_margin-8,4,en,new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0)
    def tab(self,h,r,w):
        t=sum(w); s=(self.w-2*self.l_margin)/t if t>self.w-2*self.l_margin else 1; w=[x*s for x in w]
        self.set_font('C','B',7); self.set_fill_color(45,45,75); self.set_text_color(255,255,255)
        for i,hh in enumerate(h): self.cell(w[i],5.5,hh,border=1,fill=True,align='C')
        self.ln(); self.set_text_color(0); self.set_font('C','',7)
        for ri,row in enumerate(r):
            self.set_fill_color(248,248,252) if ri%2==0 else self.set_fill_color(255,255,255)
            for i,c in enumerate(row): self.cell(w[i],5,str(c)[:70],border=1,fill=True,align='C')
            self.ln()
        self.set_x(self.l_margin); self.ln(2)

pdf=PDF('AgentWorld Async — Problems & Fixes Summary')

pdf.h1('一、发现的问题总览 (共28个)','1. Issues Discovered (Total: 28)')
pdf.tab(['类别 Category','数量 Count','严重度 Severity','状态 Status'],
    [['性能瓶颈 Performance','8','P0-P3','7 fixed, 1 planned'],
     ['外部Agent接入 External','11','P0-P2','8 fixed, 3 planned'],
     ['1小时测试发现 Test','4','P0-P1','2 fixed, 2 via prompt'],
     ['代码质量 Code Quality','5','P1-P2','All fixed 全部修复']],
    [44,24,30,90])

pdf.h1('二、性能瓶颈 — 已修复','2. Performance Bottlenecks — Fixed')
pdf.tab(['#','瓶颈 Bottleneck','解决方案 Solution','复杂度变化 Before->After'],
    [['1','LLM 线程池饱和','Brain.decide_batch() N->1次','O(n)->O(1)'],
     ['2','SensorySystem O(n*m)','SpatialGrid 空间哈希','O(n*m)->O(n*k)'],
     ['3','Busy Loop 轮询','EventBus + asyncio.Event','轮询->通知 polling->notify'],
     ['4','Inbox 消息洪水','消息限制+优先级 (prompt)','—'],
     ['5','Resolver 无缓存','resolve=rule 快速路径','LLM轮次减少'],
     ['6','EventEntity 泄露','Lifecycle.despawn + grid','统一清理 unified'],
     ['7','WS 串行广播','asyncio.gather 并发','串行->并行'],
     ['8','Drive/Attr 重复','DriveSystem 共享 dict','2份->1源 source']],
    [8,44,42,94])

pdf.h1('三、外部Agent接入 — 已修复 (8/11)','3. External Agent — Fixed (8/11)')
pdf.tab(['#','严重度 Sev','问题 Issue','修复 Fix'],
    [['1','P0','断线 Entity 残留','AgentConnection.disconnect -> lifecycle.despawn()'],
     ['2','P0','Busy 时可移动','AgentConnection 检查 status!=idle'],
     ['3','P0','无 zone 边界校验','校验 pos vs zone width/height'],
     ['4','P0','WS 轮询阻塞','asyncio.Event 替代 15s sleep'],
     ['5','P0','重连不一致','AgentConnection.accept() 复用 Entity'],
     ['6','P1','跨zone Grid bug','Lifecycle.transfer_zone()'],
     ['7','P1','无心跳检测','AgentConnection 20s 周期'],
     ['8','P1','Inbox 从不读取','AgentConnection._push_inbox()']],
    [8,16,52,112])

pdf.h1('四、1小时测试 — 关键发现','4. 1-Hour Test — Key Findings')
pdf.b('58分钟测试: 8 NPC x 3 zones, 892 次交互, 0 错误, 32/32 属性合规。',
      '58-minute test: 8 NPCs x 3 zones, 892 actions, 0 errors, 32/32 attrs ok.')
pdf.tab(['发现 Finding','数据 Data','根因 Root Cause','修复 Fix'],
    [['交谈泛滥 Talk spam','594/892 (66.6%)','交谈是 agent-type (免费)','交谈 -> resolve:llm (降至52%)'],
     ['金币耗尽 Coin depletion','4 agent 归零','LLM #2 未强制边界','世界法则 + 投影校验'],
     ['全挤酒馆 All in bar','8/8 agents','酒馆内容密度远超其他','探索规则 + 内容平衡'],
     ['动作单调 Action monotony','仅7种动作类型','缺少多样性激励','世界法则 + 自由文本动作']],
    [30,34,56,68])

pdf.h1('五、交谈比例: 改前 vs 改后','5. Talk Ratio: Before vs After')
pdf.tab(['指标 Metric','改前 Before','改后 After','变化 Delta'],
    [['交谈占比','66.6%','52%','-14pp'],
     ['动作多样性','7 种 types','16 种 types','+9'],
     ['交谈成本','0s (免费 free)','2-3s (LLM #2)','成本增加'],
     ['交谈深度','单向扔消息 one-way','生成对话 dialogue','有意义 meaningful']],
    [40,38,44,66])

pdf.h1('六、解决问题的架构设计','6. Architecture That Solved Them')
for c,e in [('世界法则 (prompt slot): 通用行为公理, 对所有Agent生效','World Rules: universal axioms applied to all agents'),
    ('交谈 LLM化: 聊天现在有成本, Agent自然选择多样化交互','Talk -> LLM #2: chat costs tokens, agents choose diverse actions'),
    ('投影+校验分离: 会计和作家是不同的人','Projection + Verify separation: accountant vs writer'),
    ('生命周期+网格: 实体清理和空间查询统一入口','Lifecycle + Grid: unified entity cleanup and spatial queries'),
    ('EventBus: 所有轮询替换为发布/订阅通知','EventBus: all polling replaced with pub/sub'),
    ('AgentConnection: 外部agent完整生命周期, 断开自清理','AgentConnection: external agent full lifecycle, disconnect self-clean')]:
    pdf.bl(c,e)

pdf.h1('七、剩余待处理问题','7. Remaining Issues (Planned)')
pdf.tab(['#','问题 Issue','严重度','状态 Status'],
    [['1','安全认证+限流 Security','P2','Planned 计划中'],
     ['2','外部agent属性可配置 Config','P2','Planned 计划中'],
     ['3','持久化 SQLite Persistence','P2','Planned 计划中'],
     ['4','Prompt 调优 Prompt tuning','P2','Iterate 迭代'],
     ['5','Godot 前端迁移 Frontend','P3','引擎稳定后 After stable']],
    [9,72,24,82])

pdf.h1('八、代码变更统计','8. Code Impact Summary')
pdf.tab(['指标 Metric','数值 Value'],
    [['源文件 .py files','42'],
     ['新增文件 New','7 (EventBus,Lifecycle,Grid,Connection,Errors,Verify,Pipeline)'],
     ['删除文件 Deleted','9 (死代码, 旧external.py, 冗余测试)'],
     ['新增行数 Lines added','~885 (核心基础设施)'],
     ['删除行数 Lines removed','~2266 (死代码 + YAML简化)'],
     ['LLM 调用点 LLM points','4 (Decision, Story, Projection, Memory)'],
     ['交互管层深度 Depth','6 layers (build->story->project->verify->memory->apply)']],
    [38,150])

pdf.output(OUT)
print(f'OK {OUT} ({os.path.getsize(OUT)} bytes)')
