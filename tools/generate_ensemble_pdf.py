#!/usr/bin/env python3
"""Generate classic ensemble timeline PDF with P/Q/KL data."""
import json,os,sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fpdf import FPDF
from collections import defaultdict

BASE=os.path.dirname(os.path.abspath(__file__)); PROJ=os.path.join(BASE,"..")
DATA=os.path.join(PROJ,"e2e_concurrent_trace.json")
with open(DATA) as f: traces=json.load(f)

FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
for r,d,files in os.walk('/usr/share/fonts'):
    for f in files:
        if 'NotoSansCJK' in f and 'Regular' in f: FONT=os.path.join(r,f); break

traces.sort(key=lambda t: t.get("ts",0))
COLORS={"杰洛特":(180,60,60),"叶奈法":(100,100,180),"丹德里恩":(180,150,100)}

class PDF(FPDF):
    def __init__(self):
        super().__init__('P','mm','A4')
        bold=FONT.replace('Regular','Bold')
        self.add_font('C','',FONT); self.add_font('C','B',bold if os.path.exists(bold) else FONT)
        self.set_auto_page_break(True,8); self.add_page()
    def header(self):
        if self.page_no()==1:
            self.set_font('C','B',16)
            self.cell(0,9,'Classic Ensemble Timeline — P/Q/KL Architecture',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_font('C','',8); self.set_text_color(100)
            self.cell(0,5,'3 Active Agents × 10min Concurrent — 302 Traces',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0); self.ln(5)
        else:
            self.set_font('C','',6); self.set_text_color(128)
            self.cell(0,5,'Ensemble Timeline',align='L'); self.cell(0,5,f'p.{self.page_no()}',align='R',new_x='LMARGIN',new_y='NEXT'); self.set_text_color(0)
    def h1(self,t):
        self.ln(2); self.set_font('C','B',11); self.set_fill_color(60,60,160); self.set_text_color(255,255,255)
        self.cell(0,6,f'  {t}',fill=True,new_x='LMARGIN',new_y='NEXT'); self.set_text_color(0); self.ln(2)
    def b(self,t,sz=6.5):
        self.set_x(self.l_margin); self.set_font('C','',sz); self.multi_cell(0,3,t); self.ln(0.3)
    def entry(self,t):
        name=t.get("agent","?"); color=COLORS.get(name,(100,100,100))
        ts=t.get("ts",0); action=t.get("action_text","")
        target=t.get("target",""); kl=t.get("kl_text","")
        result=t.get("result_narrative",""); deltas=t.get("result_caller_deltas",{})
        drives=t.get("drives",{}); coins=t.get("coins","?")
        
        self.set_font('C','B',8); self.set_text_color(*color)
        label=action[:70] if action else (f"rest at {t.get('pos',[])}")
        if target and target!=name: label+=f" → {target}"
        self.cell(0,5,f'+{ts:.0f}s  {name}  {label}',new_x='LMARGIN',new_y='NEXT')
        self.set_text_color(0)
        
        # KL divergence
        if kl:
            self.set_font('C','',6.5); self.set_text_color(120,80,120)
            self.cell(0,3.5,f'    KL: {kl[:120]}',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0)
        
        # Drives
        self.set_font('C','',6.5); self.set_text_color(100,100,100)
        self.cell(0,3.5,f'    t={drives.get("thirst","?"):.0f} h={drives.get("hunger","?"):.0f} s={drives.get("social","?"):.0f} c={coins}',new_x='LMARGIN',new_y='NEXT')
        self.set_text_color(0)
        
        # Result
        if result:
            self.set_font('C','',6.5); self.set_fill_color(252,252,255)
            self.cell(0,3.5,f'    > {result[:130]}',fill=True,new_x='LMARGIN',new_y='NEXT')
            if deltas:
                self.cell(0,3.5,f'    deltas: {deltas}',new_x='LMARGIN',new_y='NEXT')
        
        self.ln(1.5)

def build():
    pdf=PDF()
    
    # Storyline summary
    pdf.h1('Story Arc')
    pdf.b('Three active agents (杰洛特, 叶奈法, 丹德里恩) across 10 minutes. Extras (特莉丝, 卓尔坦, 兰伯特, 凯拉, 维瑟米尔) stuck in CancelledError — known asyncio.run() issue.')
    
    for name,color in [("杰洛特",COLORS["杰洛特"]),("叶奈法",COLORS["叶奈法"]),("丹德里恩",COLORS["丹德里恩"])]:
        acts=[t for t in traces if t.get("agent")==name and t.get("action_text")]
        results=[t for t in traces if t.get("agent")==name and t.get("result_narrative")]
        stories=[t for t in traces if t.get("agent")==name and isinstance(t.get("llm1_output",{}),dict) and t["llm1_output"].get("story")]
        kl_count=sum(1 for t in traces if t.get("agent")==name and t.get("kl_text"))
        pdf.b(f'{name}: {len(acts)} actions, {len(results)} results, {len(stories)} stories, {kl_count} KL traces')
    pdf.ln(2)
    
    # P/Q/KL architecture showcase
    pdf.h1('P/Q/KL Architecture in Action')
    # Find a trace with KL data
    kl_traces=[t for t in traces if t.get("kl_text") and len(t.get("kl_text",""))>10]
    if kl_traces:
        t=kl_traces[20]  # pick one with interesting KL
        pdf.b(f'Agent: {t.get("agent")} at +{t.get("ts"):.0f}s')
        pdf.b(f'Action: {t.get("action_text",\"?\")[:80]}')
        # P distribution
        p=t.get("p_distribution",{})
        if p:
            pdf.b(f'P(dist): pos={p.get("pos")} zone={p.get("zone")} interactable={p.get("interactable",[])} visible={p.get("visible",[])}')
        pdf.b(f'KL: {t.get("kl_text",\"\")}')
    
    pdf.ln(2)
    
    # Full timeline
    pdf.h1('Full Timeline')
    for t in traces:
        if t.get("action_text") or t.get("result_narrative") or t.get("kl_text"):
            pdf.entry(t)
    
    OUT=os.path.join(PROJ,"docs","AgentWorld_Async_Classic_Ensemble.pdf")
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    pdf.output(OUT); return OUT

if __name__=="__main__":
    path=build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
