#!/usr/bin/env python3
"""Generate Final Architecture PDF — Bilingual EN+CN."""
import os,sys
from fpdf import FPDF

OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','docs','AgentWorld_Async_Final_Architecture.pdf')
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
            self.set_font('C','B',18)
            self.cell(0,10,self.t,align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_font('C','',8); self.set_text_color(100)
            self.cell(0,5,'Bilingual — 中英双语',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0); self.ln(3)
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
    def fig(self,t):
        self.ln(1); self.set_font('C','',7); self.set_fill_color(248,248,255)
        for l in t.strip().split('\n'):
            self.cell(self.w-2*self.l_margin,3.8,' '+l[:120],fill=True,new_x='LMARGIN',new_y='NEXT')
        self.ln(2)

pdf=PDF('AgentWorld Async — Final Architecture')

pdf.h1('一、实体模型','1. Entity Model')
pdf.b('实体不再枚举动作。用自然语言描述自己。LLM 自由提议任何合理动作。仅 Gate 实体保留确定性规则 (zone 传送)。',
      'Entities describe themselves in natural language. LLM freely proposes any reasonable action. Only Gate entities keep deterministic rules.')
pdf.tab(['维度 Aspect','之前 Before','之后 After'],
    [['动作 Actions','YAML枚举 [饮用,嗅闻,搭话]','describe: 自然语言描述'],
     ['新实体 New entity','写action列表+cost/effects','1行 describe'],
     ['香蕉皮 Banana peel','做不到 (没写slip_on)','LLM读描述, 自然推理'],
     ['交互方式 Interaction','从固定列表选','自由文本, LLM#2裁定']],
    [30,76,82])

pdf.h1('二、Agent 自主循环','2. Agent Autonomous Loop')
pdf.b('每个Agent作为独立 asyncio Task 运行: decay → sense → think(LLM #1) → move → interact → sleep。',
      'Each agent runs as independent asyncio Task: decay -> sense -> think(LLM #1) -> move -> interact -> sleep.')
pdf.b('LLM #1 输出 — action 是自由文本，不限于预定义列表:',
      'LLM #1 output — action is free text, not constrained to a pre-defined list:')
pdf.fig('  {"thinking":"...","move_to":null,"target_entity":"banana_peel","action":"捡起来扔掉"}')
pdf.b('LLM #1 看到: 欲望状态表 + 感知(实体describe)+ 记忆(第一人称recent_info)+ 世界法则',
      'LLM #1 sees: drive state table + sensory (entities with describe) + memory (first-person recent_info) + world_rules')

pdf.h1('三、交互管线 (6层)','3. Interaction Pipeline (6 Layers)')
pdf.b('每次交互走完 6 层。3 次 LLM + 1 次代码校验。每层专注一个任务。',
      '6 layers per interaction. 3 LLMs + 1 code verify. Each layer handles one concern.')
pdf.fig('Agent triggers interaction')
pdf.fig('  -> Build Component (code): 空间BFS, radius=3, 收集分量内所有实体+describe')
pdf.fig('  -> Story Layer (LLM #2, t=0.8): 从分量全景生成客观叙事')
pdf.fig('  -> Projection Layer (LLM #3, t=0.3): 计算每实体 deltas (纯数字)')
pdf.fig('  -> Verification Layer (code): 校验 deltas. 失败->feedback->回注LLM #3重试')
pdf.fig('  -> Memory Layer (LLM #4, t=0.7): 生成每个NPC的第一人称视角记忆')
pdf.fig('  -> Apply (code): 写入 deltas, 推送 memories 到 recent_info')
pdf.b('故事与投影分离: 作家不是会计。Story separates from Projection: writer is not accountant.')

pdf.h1('四、与 v1 对照','4. Mapping to v1')
pdf.tab(['v1','v2','职责 Responsibility'],
    [['Component Split','Build Component','BFS 收集实体'],
     ['LLM #1 (Plan)','LLM #1 (Decision)','Agent 自主决策'],
     ['LLM #3 (Narrative)','Story (LLM #2)','生成客观叙事'],
     ['LLM #4a (Topo Delta)','—','v2 用空间替代图边'],
     ['LLM #5 (Projection)','Projection (LLM #3)','纯数字 deltas'],
     ['Verification Layer','Verify (code)','校验 + 反馈重试'],
     ['recent_info 写入','Memory (LLM #4)','第一人称视角记忆']],
    [44,44,100])

pdf.h1('五、世界法则 (通用Prompt Slot)','5. World Rules (Universal Prompt Slots)')
pdf.b('领域无关的公理, 通过 content provider slot 注入所有Agent prompt。换世界无须修改。',
      'Domain-agnostic axioms injected into ALL agent prompts. No modification needed for new worlds.')
pdf.h2('Agent 侧','Agent side (world_rules)')
for c,e in [('属性守恒: 不能花到负数','Attribute Conservation'),
    ('边际递减: 重复交互收益递减','Diminishing Returns'),
    ('满意即止: 欲望 30 就够了','Satisfice'),
    ('探索优先: 去没去过的地方','Explore'),
    ('互惠社交: 单向付出不可持续','Reciprocity')]: pdf.bl(c,e)
pdf.h2('投影层','Projection side (world_rules_projection)')
for c,e in [('不可透支: deltas 不能使属性变负','No Overdraft'),
    ('边际递减: 连续同动作 >2 次效果减半','Diminishing Returns'),
    ('上下文感知: 实体状态影响结果','Context-Aware'),
    ('适度随机: ±20% 波动','Moderate Random')]: pdf.bl(c,e)

pdf.h1('六、校验层','6. Verification Layer')
pdf.fig('@register("attribute_bounds","属性边界","attrs in [0,100]")')
pdf.fig('@register("entity_existence","实体存在","referenced entities must exist")')
pdf.fig('@register("conservation","度守恒","conserved items must balance")')
pdf.fig('')
pdf.fig('mask=["attribute_bounds","entity_existence","conservation"]')
pdf.fig('failures=verify(effects,mask)')
pdf.fig('if failures: feedback=build_feedback(failures); retry LLM #3')
pdf.b('借鉴 v1 校验注册表。纯代码, 零 LLM 成本。',
      'Inspired by v1 verification registry. Zero LLM cost.')

pdf.h1('七、LLM 调用全景','7. LLM Call Summary')
pdf.tab(['调用 Call','温度 Temp','频率 Frequency','用途 Purpose'],
    [['LLM #1','0.7','每轮','Agent 自主决策 Decision'],
     ['LLM #2','0.8','每次交互','故事层: 生成叙事 Story'],
     ['LLM #3','0.3','每次交互','投影层: 计算deltas Projection'],
     ['LLM #4','0.7','每次交互','记忆层: 第一人称记忆 Memory']],
    [26,16,34,112])

pdf.h1('八、基础设施','8. Infrastructure')
pdf.tab(['模块 Module','文件 File','行数 Lines','用途 Purpose'],
    [['EventBus','core/event_bus.py','41','Pub/sub, 消除所有轮询'],
     ['Lifecycle','core/lifecycle.py','79','spawn/despawn 统一入口'],
     ['SpatialGrid','core/spatial_grid.py','56','O(1) 近邻查询 (空间哈希)'],
     ['AgentConnection','agent/connection.py','280','外部agent完整生命周期'],
     ['ErrorCollector','core/error_collector.py','93','去重错误追踪 + API'],
     ['BatchDecision','agent/brain.py','+60','N agents → 1 LLM call']],
    [38,52,18,80])

pdf.h1('九、文件改动清单','9. Files Changed vs Unchanged')
pdf.tab(['状态 Status','文件 File','改动 Change'],
    [['CHANGED','world.yaml','删actions, 加describe (-200行)'],
     ['CHANGED','prompts.yaml','+3 模板, +校验mask'],
     ['CHANGED','systems/interaction.py','删action校验, +component, +verify'],
     ['CHANGED','interaction/resolver.py','拆分 Story/Projection/Memory'],
     ['NEW','core/verification.py','校验注册表+反馈 (~80行)'],
     ['NEW','core/pipeline.py','管线编排器 (~60行)'],
     ['UNCHANGED','layers/*, entity.py, brain.py','零改动'],
     ['UNCHANGED','sensory.py, spatial_grid.py','零改动'],
     ['UNCHANGED','event_bus.py, lifecycle.py','零改动']],
    [24,78,86])

pdf.h1('十、十大设计原则','10. Ten Design Principles')
for c,e in [('唯一 Entity 类','Single Entity Class: YAML differs, not subclass'),
    ('分层架构','Layer Architecture: independent visual/interaction/agent/auditory'),
    ('位置即关系','Position = Relationship: no parent/child fields'),
    ('配置即行为','Config = Behavior: all text in YAML, zero hardcoded'),
    ('Systems 总控','Systems Orchestration: cross-layer logic only in Systems'),
    ('LLM 最小化','LLM Minimization: only 4 call points'),
    ('Agent 自治','Agent Autonomy: inbox messaging, self-determined attributes'),
    ('混合异步','Hybrid Async: busy queue + inbox'),
    ('前端零知识','Frontend Agnostic: sprite renderer, zero world knowledge'),
    ('属性平权','Flat Attributes: coins == hunger, all is apply_deltas')]:
    pdf.bl(c,e)

pdf.output(OUT)
print(f'OK {OUT} ({os.path.getsize(OUT)} bytes)')
