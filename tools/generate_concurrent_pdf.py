#!/usr/bin/env python3
"""Generate concurrent E2E PDF with timeline."""
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

class PDF(FPDF):
    def __init__(self):
        super().__init__('L','mm','A4')  # Landscape for timeline
        bold=FONT.replace('Regular','Bold')
        self.add_font('C','',FONT); self.add_font('C','B',bold if os.path.exists(bold) else FONT)
        self.set_auto_page_break(True,8); self.add_page()
    def header(self):
        if self.page_no()==1:
            self.set_font('C','B',14)
            self.cell(0,8,'E2E Concurrent Test — Timeline',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_font('C','',7); self.set_text_color(100)
            self.cell(0,5,'8 Agents, 180s Concurrent, 70 Traces',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0); self.ln(5)
        else:
            self.set_font('C','',6); self.set_text_color(128)
            self.cell(0,5,'Concurrent Timeline',align='L')
            self.cell(0,5,f'p.{self.page_no()}',align='R',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0)
    def h1(self,t):
        self.ln(2); self.set_font('C','B',11); self.set_fill_color(60,60,160); self.set_text_color(255,255,255)
        self.cell(0,6,f'  {t}',fill=True,new_x='LMARGIN',new_y='NEXT'); self.set_text_color(0); self.ln(2)
    def b(self,t,sz=6.5):
        self.set_x(self.l_margin); self.set_font('C','',sz); self.multi_cell(0,3.2,t); self.ln(0.5)
    def code(self,t):
        self.set_font('C','',5.5); self.set_fill_color(248,248,255)
        for l in t.strip().split('\n'): self.cell(self.w-2*self.l_margin,3,' '+l[:140],fill=True,new_x='LMARGIN',new_y='NEXT')
        self.ln(1)

def build():
    pdf=PDF()

    # ── Timeline table ──
    pdf.h1('Timeline (0-191s, all 8 agents concurrently)')
    
    # Sort by timestamp
    traces.sort(key=lambda t: t.get("ts",0))
    
    # Build timeline rows
    agent_colors = {
        "杰洛特": (180,100,100), "叶奈法": (100,100,180),
        "丹德里恩": (180,150,100), "维瑟米尔": (150,180,100),
        "特莉丝": (100,180,100), "卓尔坦": (180,100,180),
        "凯拉": (100,180,180), "兰伯特": (150,150,150),
    }
    
    headers = ["Time","Agent","Action","Target","Zone","Drives"]
    widths = [18,20,80,22,30,50]
    pdf.set_font('C','B',6); pdf.set_fill_color(45,45,75); pdf.set_text_color(255,255,255)
    for i,h in enumerate(headers): pdf.cell(widths[i],5,h,border=1,fill=True,align='C')
    pdf.ln(); pdf.set_text_color(0); pdf.set_font('C','',5.5)
    
    colors_used = {}
    for ri,t in enumerate(traces):
        name = t.get("agent","?")
        if name not in colors_used:
            color = agent_colors.get(name, (200,200,200))
            pdf.set_text_color(*color)
            colors_used[name] = color
        else:
            pdf.set_text_color(*colors_used[name])
        
        ts = t.get("ts",0)
        ts_str = f"{ts:.0f}s"
        action = t.get("action_text","")
        if not action:
            if t.get("moved_to"): action = f"[move to {t['moved_to']}]"
            elif t.get("note")=="rest": action = "[rest]"
            else: action = t.get("note","")
        
        target = t.get("target","")
        zone = t.get("zone","?")
        drives = t.get("drives",{})
        th = float(drives.get("thirst",0)); hu = float(drives.get("hunger",0))
        d_str = f't={th:.0f} h={hu:.0f} c={t.get("coins","?")}'
        
        row = [ts_str, name, action[:45], target, zone, d_str]
        for i,c in enumerate(row): pdf.cell(widths[i],4,str(c)[:50],border=1,align='C')
        pdf.ln()
    pdf.set_text_color(0)
    pdf.ln(3)

    # ── Per-agent detail ──
    pdf.h1('Per-Agent Detail (LLM #1 outputs + results)')
    agent_groups = defaultdict(list)
    for t in traces:
        agent_groups[t.get("agent","?")].append(t)
    
    for name in ["杰洛特","叶奈法","丹德里恩","维瑟米尔","特莉丝","卓尔坦","凯拉","兰伯特"]:
        acts = agent_groups.get(name,[])
        if not acts: continue
        
        acts_with_action = [t for t in acts if t.get("action_text")]
        acts_with_result = [t for t in acts if t.get("result_narrative")]
        
        pdf.h1(f'{name}: {len(acts_with_action)} acts, {len(acts_with_result)} results')
        
        for t in acts_with_action[:4]:
            ts = t.get("ts",0)
            action = t.get("action_text","")[:60]
            target = t.get("target","")
            result = t.get("result_narrative","")
            deltas = t.get("result_caller_deltas",{})
            
            pdf.b(f'  [+{ts:.0f}s] {action} -> {target}')
            if result:
                pdf.b(f'    result: {result[:120]}')
                pdf.b(f'    deltas: {deltas}')
            lo = t.get("llm1_output",{})
            if isinstance(lo, dict):
                pdf.b(f'    LLM #1: {lo.get("thinking","")[:100]}')

    OUT=os.path.join(PROJ,"docs","AgentWorld_Async_Concurrent_Timeline.pdf")
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    pdf.output(OUT)
    return OUT

if __name__=="__main__":
    path=build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
