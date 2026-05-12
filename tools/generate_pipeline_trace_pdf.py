#!/usr/bin/env python3
"""Generate Full Pipeline Trace PDF from pipeline_trace_all.json."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fpdf import FPDF

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, "..")
DATA_FILE = os.path.join(PROJ, "pipeline_trace_all.json")

FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
for r, d, files in os.walk('/usr/share/fonts'):
    for f in files:
        if 'NotoSansCJK' in f and 'Regular' in f:
            FONT = os.path.join(r, f); break

with open(DATA_FILE) as f:
    traces = json.load(f)


class PDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        bold = FONT.replace('Regular', 'Bold')
        self.add_font('C', '', FONT)
        self.add_font('C', 'B', bold if os.path.exists(bold) else FONT)
        self.set_auto_page_break(True, 8)
        self.add_page()

    def header(self):
        if self.page_no() == 1:
            self.set_font('C', 'B', 18)
            self.cell(0, 10, 'Pipeline Trace — All 8 Agents', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_font('C', '', 9); self.set_text_color(100)
            self.cell(0, 5, 'LLM #1 (Decision) + LLM #2 (Resolve) — Raw Input/Output', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)
            self.line(self.l_margin, self.y + 2, self.w - self.r_margin, self.y + 2)
            self.ln(6)
        else:
            self.set_font('C', '', 6); self.set_text_color(128)
            self.cell(0, 5, 'Pipeline Trace Report', align='L')
            self.cell(0, 5, f'p.{self.page_no()}', align='R', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)

    def h1(self, t):
        self.ln(3); self.set_font('C', 'B', 13); self.set_fill_color(60, 60, 160)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, f'  {t}', fill=True, new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0); self.ln(2)

    def b(self, t, sz=7):
        self.set_x(self.l_margin); self.set_font('C', '', sz)
        self.multi_cell(0, 3.8, t); self.ln(0.5)

    def code_block(self, t):
        self.set_font('C', '', 6); self.set_fill_color(248, 248, 255)
        for l in t.strip().split('\n'):
            self.cell(self.w - 2 * self.l_margin, 3.5, ' ' + l[:125], fill=True, new_x='LMARGIN', new_y='NEXT')
        self.ln(2)
        self.set_font('C', '', 7)


def build():
    pdf = PDF()

    # Summary table
    pdf.h1('Summary')
    rows = []
    for t in traces:
        name = t.get('agent', '?')
        act = t.get('action', '')[:50]
        free = 'Y' if t.get('free_text') else 'N'
        vf = t.get('verify_failures', 0)
        t1 = t.get('llm1_time', 0)
        t2 = t.get('llm2_time', 0)
        rows.append([name, act, free, f'{t1}s', f'{t2}s', str(vf)])
    pdf.set_font('C', 'B', 7); pdf.set_fill_color(45, 45, 75); pdf.set_text_color(255, 255, 255)
    wid = [18, 65, 12, 16, 16, 12]
    for i, h in enumerate(['Agent', 'Action', 'Free', 'LLM#1', 'LLM#2', 'Verif']):
        pdf.cell(wid[i], 5, h, border=1, fill=True, align='C')
    pdf.ln(); pdf.set_text_color(0); pdf.set_font('C', '', 6.5)
    for ri, row in enumerate(rows):
        pdf.set_fill_color(248, 248, 252) if ri % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        for i, c in enumerate(row):
            pdf.cell(wid[i], 4.5, str(c)[:55], border=1, fill=True, align='C')
        pdf.ln()
    pdf.set_x(pdf.l_margin); pdf.ln(3)

    pdf.b(f'Total time: {sum(t["llm1_time"]+t["llm2_time"] for t in traces):.0f}s  |  '
          f'All free-text: {all(t["free_text"] for t in traces)}  |  '
          f'Verification: {sum(1 for t in traces if t["verify_failures"]==0)}/{len(traces)} clean')

    # Per-agent traces
    for i, t in enumerate(traces):
        name = t.get('agent', f'Agent {i+1}')
        if 'error' in t:
            pdf.h1(f'{name}: ERROR — {t["error"]}')
            continue

        pdf.h1(f'{name}: {t["action"][:80]}')
        pdf.b(f'Zone: {t["zone"]} pos={t["pos"]} -> target: {t["target"]} ({t["target_id"]})')
        pdf.b(f'Free-text: {t["free_text"]} | Component: {t.get("component",[])}')
        pdf.b(f'LLM #1: {t["llm1_time"]}s | LLM #2: {t["llm2_time"]}s | Verify: {t["verify_failures"]} failures')

        pdf.b('=== LLM #1 INPUT (Decision Prompt) ===', 6.5)
        pdf.code_block(t['llm1_prompt'][:800])

        out1 = t['llm1_output']
        if isinstance(out1, dict):
            pdf.b(f'=== LLM #1 OUTPUT ===')
            pdf.code_block(json.dumps(out1, ensure_ascii=False, indent=2)[:500])

        pdf.b('=== LLM #2 INPUT (Resolver Prompt) ===', 6.5)
        pdf.code_block(t['llm2_prompt'][:600])

        pdf.b(f'=== LLM #2 OUTPUT (Resolver Result) ===')
        pdf.b(f'  narrative: {t["llm2_narrative"][:200]}')
        pdf.b(f'  caller_deltas: {t["llm2_caller_deltas"]}')
        pdf.b(f'  target_deltas: {t["llm2_target_deltas"]}')
        if t.get("llm2_ambient_effects"):
            pdf.b(f'  ambient_effects: {t["llm2_ambient_effects"]}')
        pdf.b(f'  public_observation: {t.get("llm2_public_observation","")[:120]}')
        if t.get("verify_feedback") and t["verify_feedback"] != "pass":
            pdf.b(f'  verify_feedback: {t["verify_feedback"][:200]}', 6.5)

    OUT = os.path.join(PROJ, "docs", "AgentWorld_Async_Pipeline_Trace.pdf")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pdf.output(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
