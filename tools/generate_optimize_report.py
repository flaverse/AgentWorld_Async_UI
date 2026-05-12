#!/usr/bin/env python3
"""Generate optimization report PDF from test analysis."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fpdf import FPDF

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "..", "docs", "AgentWorld_Async_1Hour_Optimization.pdf")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
for root, _, files in os.walk("/usr/share/fonts"):
    for f in files:
        if "NotoSansCJK" in f and "Regular" in f:
            FONT_PATH = os.path.join(root, f); break

class PDF(FPDF):
    def __init__(self):
        super().__init__('P','mm','A4')
        bold = FONT_PATH.replace("Regular","Bold")
        self.add_font("CN","",FONT_PATH)
        self.add_font("CN","B",bold if os.path.exists(bold) else FONT_PATH)
        self.set_auto_page_break(True,12)
        self.add_page()

    def header(self):
        if self.page_no()==1:
            self.set_font("CN","B",19)
            self.cell(0,10,"1-Hour Test — Optimization Report",align="C",new_x="LMARGIN",new_y="NEXT")
            self.set_font("CN","",9); self.set_text_color(100)
            self.cell(0,6,"Performance Analysis & Improvement Suggestions",align="C",new_x="LMARGIN",new_y="NEXT")
            self.set_text_color(0)
            self.line(self.l_margin,self.y+2,self.w-self.r_margin,self.y+2); self.ln(8)
        else:
            self.set_font("CN","",7); self.set_text_color(128)
            self.cell(0,5,"Optimization Report",align="L")
            self.cell(0,5,f"p.{self.page_no()}",align="R",new_x="LMARGIN",new_y="NEXT")
            self.set_text_color(0)

    def h1(self,t): self.ln(3); self.set_font("CN","B",14); self.cell(0,8,t,new_x="LMARGIN",new_y="NEXT"); self.ln(2)
    def h2(self,t): self.ln(1); self.set_font("CN","B",10); self.cell(0,7,t,new_x="LMARGIN",new_y="NEXT"); self.ln(1)
    def body(self,t): self.set_font("CN","",8.5); self.multi_cell(0,5,t); self.ln(1)
    def bullet(self,t): self.set_font("CN","",8.5); self.cell(self.w-2*self.l_margin,5,"  - "+t,new_x="LMARGIN",new_y="NEXT")
    def tab(self,h,r,w):
        total=sum(w)
        if total>self.w-2*self.l_margin: scale=(self.w-2*self.l_margin)/total; w=[s*scale for s in w]
        self.set_font("CN","B",7); self.set_fill_color(50,50,80); self.set_text_color(255,255,255)
        for i,hh in enumerate(h): self.cell(w[i],5.5,hh,border=1,fill=True,align='C')
        self.ln(); self.set_text_color(0); self.set_font("CN","",7)
        for ri,row in enumerate(r):
            self.set_fill_color(248,248,252) if ri%2==0 else self.set_fill_color(255,255,255)
            for i,c in enumerate(row): self.cell(w[i],5,str(c)[:60],border=1,fill=True,align='C')
            self.ln()
        self.set_x(self.l_margin); self.ln(2)

def build():
    pdf = PDF()

    pdf.h1("一、测试结果总览")
    pdf.tab(
        ["Agent","Actions","Top Action","2nd","3rd","Zone","Coins","Mood"],
        [
            ["杰洛特","125","交谈x106","搭话x8","查看委托x4","bar_zone","86","100"],
            ["叶奈法","95","交谈x78","搭话x3","研究配方x2","bar_zone","447","86"],
            ["丹德里恩","125","交谈x99","搭话x21","饮用x4","bar_zone","0","100"],
            ["维瑟米尔","105","交谈x48","搭话x44","饮用x13","bar_zone","0","100"],
            ["特莉丝","104","交谈x67","搭话x33","饮用x3","bar_zone","118","77"],
            ["卓尔坦","105","交谈x47","搭话x43","饮用x15","bar_zone","276","100"],
            ["凯拉","112","交谈x70","搭话x31","饮用x8","bar_zone","0","100"],
            ["兰伯特","121","交谈x79","搭话x36","饮用x5","bar_zone","0","100"],
        ],
        [22,18,26,24,28,24,20,16]
    )
    pdf.body("8 agents, 58.2 min, 892 total actions, 0 errors, 32/32 attribute checks passed.")
    pdf.body("All agents migrated to bar_zone. 4 agents depleted coins to zero.")

    pdf.h1("二、核心问题：交谈泛滥 (66.6% of actions)")
    pdf.body("892 次交互中，594 次 (66.6%) 是 agent-to-agent '交谈'——即发 inbox 消息给另一个 agent。")
    pdf.body("为什么这是问题：")
    pdf.bullet("交谈不调 LLM — 只是 world.send_message()，瞬间完成，不消耗 token")
    pdf.bullet("但接收方的 inbox.messages 被 drain() 后立即丢弃，没有 agent 读取或回复")
    pdf.bullet("594 条消息全是单向的，无对话，无意义交互")
    pdf.bullet("每个 agent 每分钟发送 ~15 条消息，但从未收到过回复")
    pdf.bullet("这浪费了 'action slots' — 本可以做更有意义的交互（喝东西、看草药、看公告板）")

    pdf.body("谁收到了最多消息：维瑟米尔 204 次、丹德里恩 178 次、叶奈法 74 次")
    pdf.body("为什么 agent 选择交谈：LLM prompt 里看到其他 agent 在附近，social 值高，自然选择聊天。但聊天没有反馈，LLM 不知道'没人理我'，所以一直聊。")

    pdf.h2("解决方案")
    pdf.bullet("限流：每个 agent 每秒最多发 1 条 inbox 消息")
    pdf.bullet("反馈：inbox 消息被 drain 时，自动给发送方回一条系统消息 ('对方正在忙')")
    pdf.bullet("冷却：连续发 3 条没人回后，LLM 被告知 '对方没回应'")

    pdf.h1("三、搭话泛滥 (24.5% of actions)")
    pdf.body("219 次'搭话'——与吧台老板聊天。每次调 LLM #2 裁判，消耗 tokens + 3-5 秒。")
    pdf.body("问题：搭话没有明确的目标或效果。老板只是'微微点头'，属性变化很小 (social+2, mood+1)。Agent 重复搭话却得不到实际收益。")

    pdf.h2("解决方案")
    pdf.bullet("搭话限流：同一 agent 对同一目标 30 秒内最多搭话 1 次")
    pdf.bullet("搭话加记忆提示：'你刚才已经和他聊过了，他看起来有点不耐烦'")
    pdf.bullet("多样化：增加更多交互选项（点菜/问路/打听消息），降低搭话的单调性")

    pdf.h1("四、全挤到酒馆 (all agents in bar_zone)")
    pdf.body("8 个 agent 全部从初始 zone 移动到了 bar_zone。原因：")
    pdf.bullet("bar_zone 是可交互实体最密集的 zone (吧台+麦酒+葡萄酒+散桌+公告板+其他 agent)")
    pdf.bullet("LLM 被丰富的交互选项吸引")
    pdf.bullet("其他 zone 内容相对贫乏 (square 只有水井/长椅/商人，herb_hut 只有草药架)")
    pdf.bullet("没有'离开酒吧回家'的反向驱动力")

    pdf.h2("解决方案")
    pdf.bullet("增加其他 zone 的内容密度 (square: 加面包摊/铁匠铺/布告栏；herb_hut: 加更多炼金设备)")
    pdf.bullet("增加'回家'驱动力：energy 低于某个值时，agent 倾向于回到自己的初始 zone")
    pdf.bullet("zone 容量上限：每个 zone 最多容纳 N 个 agent，满员后限制进入")

    pdf.h1("五、Coin 耗尽 (4 agents at 0)")
    pdf.body("4 个 agent 喝光了所有钱 (丹德里恩/维瑟米尔/凯拉/兰伯特)。累计消耗 1,154 coins。")
    pdf.body("LLM #2 裁判的提示词中已要求 'coins不能为负'，但裁判仍允许 agent 花到 0。")
    pdf.h2("解决方案")
    pdf.bullet("强制检查：InteractionSystem.submit() 前检查 agent coins >= action cost (rule 模式)")
    pdf.bullet("LLM prompt 强化：'如果发起方 coins 不足，拒绝交互，返回 narrative: \"钱不够\"'")
    pdf.bullet("增加赚钱途径：完成委托→获得 coins (目前无此机制)")

    pdf.h1("六、性能数据")
    pdf.tab(
        ["指标","值","说明"],
        [
            ["Avg action interval","3.8s","相邻动作间隔 (不含agent切换)"],
            ["Avg actions/s","0.27","每agent每秒动作数"],
            ["Avg per-agent time","437s","预算 420s, 开销来自LLM resolver调用"],
            ["LLM #1 calls","~1200","每个think 1次 (estimate)"],
            ["LLM #2 calls","274","resolve=llm 的搭话+饮用"],
            ["Passive-rule","24","零LLM成本的规则动作"],
            ["Zone crossings","7","Gate穿越"],
            ["Unique entities visited","~10","集中在少数几个 (吧台/麦酒/公告板/水井)"],
        ],
        [40,26,122]
    )

    pdf.h1("七、优先优化清单")
    pdf.tab(
        ["优","项","问题","修复","影响"],
        [
            ["P0","交谈泛滥","66.6%动作无意义","限流+反馈+冷却","减少无意义LLM distraction"],
            ["P0","Coin耗尽","4 agents破产","强制检查+强化prompt","经济系统闭环"],
            ["P1","搭话泛滥","24.5%动作重复","限流+多样化","节省LLM #2 token"],
            ["P1","全挤酒馆","无zone分布","内容平衡+驱动力","真实感+分散LLM视野"],
            ["P2","内容贫乏","其他zone太稀疏","增加实体密度","平衡交互机会分布"],
        ],
        [10,28,52,52,46]
    )

    pdf.output(OUT)
    return OUT

if __name__ == "__main__":
    path = build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
