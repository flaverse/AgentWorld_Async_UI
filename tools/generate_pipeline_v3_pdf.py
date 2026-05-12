#!/usr/bin/env python3
"""Generate LLM Pipeline v3 documentation PDF."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fpdf import FPDF

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, "..")

FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
for r, d, files in os.walk('/usr/share/fonts'):
    for f in files:
        if 'NotoSansCJK' in f and 'Regular' in f: FONT = os.path.join(r, f); break


class PDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        bold = FONT.replace('Regular', 'Bold')
        self.add_font('C', '', FONT)
        self.add_font('C', 'B', bold if os.path.exists(bold) else FONT)
        self.set_auto_page_break(True, 10)
        self.add_page()

    def header(self):
        if self.page_no() == 1:
            self.set_font('C', 'B', 18)
            self.cell(0, 10, 'LLM Pipeline v3', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_font('C', '', 9); self.set_text_color(100)
            self.cell(0, 5, 'Story-First, Per-Agent Projection, Verified Feedback Loop', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0); self.ln(8)
        else:
            self.set_font('C', '', 6); self.set_text_color(128)
            self.cell(0, 5, 'LLM Pipeline v3', align='L')
            self.cell(0, 5, f'p.{self.page_no()}', align='R', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)

    def h1(self, t):
        self.ln(3); self.set_font('C', 'B', 13); self.set_fill_color(60, 60, 160); self.set_text_color(255, 255, 255)
        self.cell(0, 7, f'  {t}', fill=True, new_x='LMARGIN', new_y='NEXT'); self.set_text_color(0); self.ln(2)

    def h2(self, t):
        self.ln(1); self.set_font('C', 'B', 10); self.cell(0, 6, t, new_x='LMARGIN', new_y='NEXT'); self.ln(1)

    def b(self, t, sz=8):
        self.set_x(self.l_margin); self.set_font('C', '', sz)
        self.multi_cell(0, 4, t); self.ln(0.5)

    def bl(self, t):
        self.set_font('C', '', 8); self.cell(self.w - 2 * self.l_margin, 4.5, '  - ' + t, new_x='LMARGIN', new_y='NEXT')

    def code(self, t):
        self.set_font('C', '', 6.5); self.set_fill_color(248, 248, 255)
        for l in t.strip().split('\n'): self.cell(self.w - 2 * self.l_margin, 3.5, ' ' + l[:130], fill=True, new_x='LMARGIN', new_y='NEXT')
        self.ln(2)

    def fig(self, t):
        self.set_font('C', '', 6.5); self.set_fill_color(250, 250, 255)
        for l in t.strip().split('\n'): self.cell(self.w - 2 * self.l_margin, 3.5, ' ' + l[:130], fill=True, new_x='LMARGIN', new_y='NEXT')
        self.ln(2)

    def tab(self, h, r, w):
        t = sum(w); s = (self.w - 2 * self.l_margin) / t if t > self.w - 2 * self.l_margin else 1; w = [x * s for x in w]
        self.set_font('C', 'B', 7); self.set_fill_color(45, 45, 75); self.set_text_color(255, 255, 255)
        for i, hh in enumerate(h): self.cell(w[i], 5.5, hh, border=1, fill=True, align='C')
        self.ln(); self.set_text_color(0); self.set_font('C', '', 7)
        for ri, row in enumerate(r):
            self.set_fill_color(248, 248, 252) if ri % 2 == 0 else self.set_fill_color(255, 255, 255)
            for i, c in enumerate(row): self.cell(w[i], 5, str(c)[:60], border=1, fill=True, align='C')
            self.ln()
        self.set_x(self.l_margin); self.ln(2)


def build():
    pdf = PDF()

    pdf.h1('1. Problem Statement')
    pdf.b('v2 pipeline has two critical issues discovered during concurrent testing:')
    pdf.h2('1.1 Stale Data (Decision-Reality Gap)')
    pdf.b('In concurrent mode, Agent A makes a decision based on sensory data that is 2-3 seconds old by the time the action executes. Agent B may have moved during that window, causing contradictions like "Triss is at the tavern table" when she actually just left for the herb hut.')
    pdf.fig('T=0s   Agent A sense(): Triss is at [35,15]')
    pdf.fig('T=2s   Agent A think(LLM #1): "go talk to Triss"')
    pdf.fig('T=3s   Agent B think(LLM #1): "go to herb hut" -> move')
    pdf.fig('T=4s   Agent A move() -> arrive, but Triss is gone')
    pdf.fig('T=5s   Agent A submit("talk to Triss", target=Triss) -> CONTRADICTION')

    pdf.h2('1.2 Attribute Adjudication Boundary')
    pdf.b('When Agent A talks to Agent B, whose LLM decides B\'s attribute changes?')
    pdf.bl('Separation approach (v2 current): LLM #2 decides both -> violates Agent Autonomy')
    pdf.bl('Merge approach: LLM #1 decides both -> same violation')
    pdf.bl('Inbox approach: each decides their own -> loses context of the shared event')

    pdf.h1('2. New Pipeline (v3)')
    pdf.b('LLM #1 generates a SHARED STORY. Each agent\'s LLM #2 independently projects their OWN deltas from the same story. Verification layer validates combined deltas and feeds back to LLM #1 on failure.')

    pdf.fig('Agent A (杰洛特):')
    pdf.fig('  LLM #1 -> {thinking, move_to, action, story}')
    pdf.fig('  story: "杰洛特走近兰伯特，压低声音问起维瑟米尔信中的狼影线索..."')
    pdf.fig('')
    pdf.fig('Agent B (兰伯特) set to busy, receives story:')
    pdf.fig('')
    pdf.fig('Both agents independently:')
    pdf.fig('  LLM #2 (projection) -> "{self_deltas: {social:-3, mood:+2}} }"')
    pdf.fig('')
    pdf.fig('Verification Layer:')
    pdf.fig('  Merge deltas [Agent A, Agent B] -> check bounds, conservation')
    pdf.fig('  PASS -> apply deltas + record memories')
    pdf.fig('  FAIL -> build_feedback() -> retry LLM #1 with feedback')

    pdf.h1('3. How It Solves Each Problem')

    pdf.h2('3.1 Stale Data Solution')
    pdf.bl('Before LLM #1: sense() captures current state')
    pdf.bl('After LLM #1 + move: re-sense() + can_interact guard')
    pdf.bl('submit() validates target is STILL in interaction range')
    pdf.bl('Target agent is set to BUSY -> cannot move away mid-interaction')
    pdf.bl('Result: no stale data contradiction possible')

    pdf.h2('3.2 Attribute Boundary Solution')
    pdf.bl('Each agent\'s LLM #2 projects their OWN deltas independently')
    pdf.bl('Story is shared (same narrative input) but projection is private')
    pdf.bl('Agent Autonomy preserved: you decide your own mood change')
    pdf.bl('Verification ensures combined deltas respect world rules')

    pdf.h1('4. Comparison: v2 vs v3')

    pdf.tab(
        ['Aspect', 'v2 (Current)', 'v3 (New)'],
        [
            ['Story source', 'LLM #2 resolver', 'LLM #1 (caller)'],
            ['Delta source', 'LLM #2 (both parties)', 'LLM #2 (each party own)'],
            ['Agent Autonomy', 'Violated (external adjudication)', 'Preserved (self-projection)'],
            ['Stale data', 'Possible (no re-sense)', 'Prevented (re-sense + busy lock)'],
            ['LLM calls/interaction', '2 (LLM#1 + LLM#2)', '3 (LLM#1 + LLM#2x2)'],
            ['Verification', 'Post-apply only', 'Pre-apply + feedback retry'],
            ['Feedback loop', 'None', 'LLM #1 retry on verify fail'],
        ],
        [38, 58, 92],
    )

    pdf.h1('5. LLM #1 Output Schema (v3)')

    pdf.code('''
{
  "thinking": "兰伯特就在附近，聊聊维瑟米尔信里的狼影线索",
  "move_to": [20, 10],
  "action": "问问兰伯特对信中狼影线索的看法",
  "story": "杰洛特走到兰伯特桌前，拉把椅子坐下，压低声音问：'兰伯特，
           维瑟米尔的信你看了吧。发光狼影和魔法灼伤——你往南走前听说过
           类似的案子吗？'兰伯特放下麦酒，手指敲着桌面，半晌才开口..."
}''')

    pdf.h1('6. LLM #2 Output Schema (v3, per-agent)')
    pdf.code('''
// 杰洛特's LLM #2 projection:
{
  "deltas": {"social": -2, "mood": 3, "energy": -1}
}

// 兰伯特's LLM #2 projection:
{
  "deltas": {"social": -3, "mood": 2}
}''')

    pdf.h1('7. Verification Flow')
    pdf.fig('combined_deltas = [geralt_deltas, lambert_deltas]')
    pdf.fig('failures = verifier.verify(combined_deltas, world.entities)')
    pdf.fig('if failures:')
    pdf.fig('  feedback = build_feedback(failures)')
    pdf.fig('  retry LLM #1 with: "Previous attempt failed: {feedback}"')
    pdf.fig('else:')
    pdf.fig('  apply_deltas(geralt, geralt_deltas)')
    pdf.fig('  apply_deltas(lambert, lambert_deltas)')
    pdf.fig('  both.memory.record(story)')

    pdf.h1('8. Code Changes')

    pdf.tab(
        ['File', 'Change', 'Lines'],
        [
            ['prompts.yaml', 'LLM #1 output adds story field', '+3'],
            ['prompts.yaml', 'LLM #2 projection template (already exists)', '0'],
            ['Agent loop', 're-sense after move + can_interact guard', '+5'],
            ['Agent loop', 'set target busy + story delivery', '+8'],
            ['systems/interaction.py', 'submit_story() replaces submit()', '+40'],
            ['systems/interaction.py', 'per-agent LLM #2 projection', '+20'],
            ['core/verification.py', 'feedback-to-LLM#1 retry path (already built)', '0'],
        ],
        [50, 100, 18],
    )

    pdf.b('\nTotal: ~76 new lines. Existing architecture unchanged (layers, entity, sensory, grid, lifecycle, event_bus all untouched).')

    pdf.h1('9. Cost Analysis')
    pdf.tab(
        ['Metric', 'v2', 'v3', 'Delta'],
        [
            ['LLM calls per interaction', '2', '3', '+1'],
            ['LLM tokens per interaction', '~1400', '~1800', '+400'],
            ['Per-agent autonomy', 'None', 'Full', 'Fixed'],
            ['Stale data risk', 'Present', 'Eliminated', 'Fixed'],
            ['Verification', 'Post-apply', 'Pre-apply + retry', 'Stronger'],
        ],
        [56, 28, 28, 76],
    )

    OUT = os.path.join(PROJ, "docs", "AgentWorld_Async_LLM_Pipeline_v3.pdf")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pdf.output(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
