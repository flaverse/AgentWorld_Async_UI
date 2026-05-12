#!/usr/bin/env python3
"""Generate E2E integration test PDF from e2e_trace.json."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fpdf import FPDF

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, "..")
DATA = os.path.join(PROJ, "e2e_trace.json")

FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
for r,d,files in os.walk('/usr/share/fonts'):
    for f in files:
        if 'NotoSansCJK' in f and 'Regular' in f: FONT = os.path.join(r,f); break

with open(DATA) as f: traces = json.load(f)

class PDF(FPDF):
    def __init__(self):
        super().__init__('P','mm','A4')
        bold = FONT.replace('Regular','Bold')
        self.add_font('C','',FONT); self.add_font('C','B',bold if os.path.exists(bold) else FONT)
        self.set_auto_page_break(True,8); self.add_page()
    def header(self):
        if self.page_no()==1:
            self.set_font('C','B',18)
            self.cell(0,10,'E2E Integration Test Report',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_font('C','',8); self.set_text_color(100)
            self.cell(0,5,'8 Agents — Full Pipeline Trace with Timestamps',align='C',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0); self.line(self.l_margin,self.y+2,self.w-self.r_margin,self.y+2); self.ln(6)
        else:
            self.set_font('C','',6); self.set_text_color(128)
            self.cell(0,5,'E2E Trace Report',align='L'); self.cell(0,5,f'p.{self.page_no()}',align='R',new_x='LMARGIN',new_y='NEXT')
            self.set_text_color(0)
    def h1(self,t):
        self.ln(3); self.set_font('C','B',12); self.set_fill_color(60,60,160); self.set_text_color(255,255,255)
        self.cell(0,6.5,f'  {t}',fill=True,new_x='LMARGIN',new_y='NEXT'); self.set_text_color(0); self.ln(2)
    def b(self,t,sz=7):
        self.set_x(self.l_margin); self.set_font('C','',sz); self.multi_cell(0,3.5,t); self.ln(0.5)
    def code(self,t):
        self.set_font('C','',5.5); self.set_fill_color(248,248,255)
        for l in t.strip().split('\n'): self.cell(self.w-2*self.l_margin,3.2,' '+l[:130],fill=True,new_x='LMARGIN',new_y='NEXT')
        self.ln(1.5); self.set_font('C','',7)

def build():
    pdf = PDF()
    pdf.h1('Summary')
    agents = sorted(set(t.get('agent','?') for t in traces if t.get('agent')))
    actions = [t for t in traces if t.get('action_text')]
    rests = [t for t in traces if t.get('note')=='rest']
    moves_only = [t for t in traces if t.get('moved_to') and not t.get('action_text')]

    pdf.b(f'Agents: {len(agents)}  |  Traces: {len(traces)}  |  Actions: {len(actions)}')
    pdf.b(f'Rests chosen: {len(rests)}  |  Move-only: {len(moves_only)}  |  '
          f'LLM #1 time: {sum(t["llm1_time"] for t in traces if "llm1_time" in t):.0f}s')
    if traces:
        first_ts = traces[0].get("wall", "?")
        last_ts = traces[-1].get("wall", "?")
        pdf.b(f'Timestamps: {first_ts} — {last_ts}')

    for i, t in enumerate(traces):
        name = t.get('agent', f'trace_{i}')
        wall = t.get('wall','')[-12:] if t.get('wall') else ''
        note = t.get('note','')
        action = t.get('action_text','')
        target = t.get('target','')
        moved = t.get('moved_to','')
        t1 = t.get('llm1_time',0)
        t2 = t.get('llm2_time',0)

        title = f'{name}  |  {wall}'
        if action: title += f'  |  {action[:50]}... → {target}'
        elif moved: title += f'  |  moved to {moved}'
        elif note == 'rest': title += '  |  😴 Rested'
        elif note: title += f'  |  {note}'
        title += f'  |  LLM1={t1}s'
        if t2: title += f'  LLM2={t2}s'

        pdf.h1(title)

        # Drives and coins
        drives = t.get('drives',{})
        coins = t.get('coins','?')
        pos = t.get('pos',[])
        zone = t.get('zone','?')
        thirst = drives.get("thirst", "?")
        hunger = drives.get("hunger", "?")
        social = drives.get("social", "?")
        energy = drives.get("energy", "?")
        fun = drives.get("fun", "?")
        pdf.b(f'Zone={zone} pos={pos}  |  thirst={thirst} hunger={hunger} coins={coins} '
              f'social={social} energy={energy} fun={fun}')

        if note == 'rest':
            pdf.b('Agent chose to rest — both move_to and action were null.')
        elif note:
            pdf.b(f'Note: {note}')
            if t.get('llm1_prompt'):
                pdf.b('--- LLM #1 PROMPT (abbreviated) ---', 6)
                pdf.code(t['llm1_prompt'][:500])
        elif action and t.get('llm1_prompt'):
            pdf.b('--- LLM #1 PROMPT (decision) ---', 6)
            pdf.code(t['llm1_prompt'][:400])
            pdf.b(f'--- LLM #1 OUTPUT ---')
            pdf.code(json.dumps(t.get('llm1_output',{}), ensure_ascii=False, indent=2)[:400])
            if t.get('llm2_prompt'):
                pdf.b(f'--- LLM #2 PROMPT (resolver) ---', 6)
                pdf.code(t['llm2_prompt'][:400])
        elif moved and t.get('llm1_prompt'):
            pdf.b('--- LLM #1 PROMPT (move-only) ---', 6)
            pdf.code(t['llm1_prompt'][:300])

    OUT = os.path.join(PROJ, "docs", "AgentWorld_Async_E2E_Test_Report.pdf")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pdf.output(OUT)
    return OUT

if __name__ == "__main__":
    path = build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
