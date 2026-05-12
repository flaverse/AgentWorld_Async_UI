#!/usr/bin/env python3
"""Generate trio interaction timeline PDF (杰洛特, 特莉丝, 兰伯特)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from fpdf import FPDF

BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(BASE, "..")
DATA = os.path.join(PROJ, "e2e_concurrent_trace.json")
with open(DATA) as f: traces = json.load(f)

FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
for r, d, files in os.walk('/usr/share/fonts'):
    for f in files:
        if 'NotoSansCJK' in f and 'Regular' in f: FONT = os.path.join(r, f); break

TRIO = {"杰洛特", "特莉丝", "兰伯特"}

# Filter trio traces, sort by time
trio_traces = [t for t in traces if t.get("agent") in TRIO]
trio_traces.sort(key=lambda t: t.get("ts", 0))

COLORS = {
    "杰洛特": (180, 60, 60),
    "特莉丝": (60, 120, 60),
    "兰伯特": (60, 60, 180),
}


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
            self.set_font('C', 'B', 16)
            self.cell(0, 9, '杰洛特 × 特莉丝 × 兰伯特 — Interaction Timeline', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_font('C', '', 8); self.set_text_color(100)
            self.cell(0, 5, 'Concurrent E2E Test — Raw Output + Memory + Timestamps', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)
            self.line(self.l_margin, self.y + 2, self.w - self.r_margin, self.y + 2)
            self.ln(6)
        else:
            self.set_font('C', '', 6); self.set_text_color(128)
            self.cell(0, 5, 'Trio Interaction Timeline', align='L')
            self.cell(0, 5, f'p.{self.page_no()}', align='R', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)

    def entry(self, t):
        name = t.get("agent", "?")
        color = COLORS.get(name, (100, 100, 100))
        ts = t.get("ts", 0)
        action = t.get("action_text", "")
        target = t.get("target", "")
        moved = t.get("moved_to", "")
        note = t.get("note", "")
        result_narr = t.get("result_narrative", "")
        result_deltas = t.get("result_caller_deltas", {})
        result_target_deltas = t.get("result_target_deltas", {})
        zone = t.get("zone", "?")
        drives = t.get("drives", {})
        coins = t.get("coins", "?")
        llm_out = t.get("llm1_output", {})
        llm_prompt = t.get("llm1_prompt", "")

        # Header line
        self.set_font('C', 'B', 9)
        self.set_text_color(*color)
        action_label = action[:80] if action else (f"[move to {moved}]" if moved else f"[{note}]")
        social_marker = "  💬" if target and target != name else ""
        self.cell(0, 5.5, f'+{ts:.0f}s  {name}{social_marker}', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0)

        # Action
        self.set_font('C', '', 8)
        self.set_text_color(*color)
        self.cell(0, 4.5, f'  {action_label}', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0)
        self.set_font('C', '', 7); self.set_text_color(100)
        th = drives.get("thirst", "?"); hu = drives.get("hunger", "?")
        try: th = float(th); th = f"{th:.0f}"
        except: pass
        try: hu = float(hu); hu = f"{hu:.0f}"
        except: pass
        self.cell(0, 4, f'  zone={zone} pos={t.get("pos",[])}  t={th} h={hu} coins={coins}', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0)

        # LLM #1 thinking
        if isinstance(llm_out, dict) and llm_out.get("thinking"):
            self.set_font('C', '', 7); self.set_fill_color(248, 248, 255)
            self.cell(0, 4, f'  💭 {llm_out["thinking"][:120]}', fill=True, new_x='LMARGIN', new_y='NEXT')

        # LLM #2 result
        if result_narr:
            self.set_font('C', 'B', 7)
            self.set_text_color(80, 80, 80)
            self.cell(0, 4, '  ✦ RESULT (LLM #2):', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)
            self.set_font('C', '', 7); self.set_fill_color(252, 252, 255)
            self.cell(0, 4, f'  {result_narr[:150]}', fill=True, new_x='LMARGIN', new_y='NEXT')
            if result_deltas:
                self.set_font('C', '', 6.5)
                self.cell(0, 3.5, f'  caller_deltas: {result_deltas}', new_x='LMARGIN', new_y='NEXT')
            if result_target_deltas:
                self.cell(0, 3.5, f'  target_deltas: {result_target_deltas}', new_x='LMARGIN', new_y='NEXT')

        # Memory (LLM #4) — from the result narrative since LLM #4 wasn't fully active
        if result_narr:
            self.set_font('C', '', 6.5)
            self.set_text_color(60, 60, 130)
            self.cell(0, 3.5, f'  memory: {result_narr[:120]}', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)

        self.ln(2)

    def storyline(self):
        self.set_font('C', 'B', 10); self.set_fill_color(60, 60, 160); self.set_text_color(255, 255, 255)
        self.cell(0, 6, '  Story Arc — 3-Minute Hunt', fill=True, new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0); self.ln(3)
        self.set_font('C', '', 7.5)
        story_steps = [
            (0, "三人各自在广场活动 — 杰洛特水井打水，兰伯特也在井边，特莉丝看商人摊位"),
            (10, "兰伯特主动搭话杰洛特: '老狼，站水井边发呆可不像你'"),
            (15, "特莉丝加入: '两位，要不要去看看商人在卖什么?'"),
            (21, "兰伯特提议去酒馆: '我请你去狐狸与鹅喝一杯'"),
            (40, "酒吧集结 — 兰伯特把维瑟米尔信拍桌上: '老家伙来信了，凯尔莫罕墙要修'"),
            (52, "杰洛特问特莉丝: '你感应到什么异常吗?' — 三人开始讨论信的内容"),
            (70, "讨论深入 — '发光狼影、魔法灼伤、远古咒语'"),
            (100, "兰伯特去水井查看: 发现井壁新爪痕，井底有金属摩擦声"),
            (112, "兰伯特仔细观察爪痕: '爪痕很新，特莉丝感觉到了古老魔力波动'"),
            (126, "兰伯特紧急回酒馆: '井里有东西——我们找到线索了'"),
            (142, "特莉丝举起焦黑树皮碎片: '这更像是被束缚的意识在消散'"),
            (156, "特莉丝分析魔法残留: '人的叹息+枯萎玫瑰气味——古老魔法痕迹'"),
            (171, "特莉丝提议休息: '今晚谜团先放一放。我请你们喝一杯！'"),
            (173, "兰伯特最后定调: '明天一早带齐家伙，先下井看看。今晚别单独行动'"),
            (176, "杰洛特关联线索: '尼弗迦德项圈狼人可能有关联'"),
            (181, "特莉丝放松气氛，叫丹德里恩弹《白果园的月光舞曲》"),
        ]
        for ts, text in story_steps:
            self.cell(0, 4, f'  +{ts:3d}s  {text}', new_x='LMARGIN', new_y='NEXT')
        self.ln(3)

    def memory_section(self):
        self.set_font('C', 'B', 10); self.set_fill_color(60, 60, 160); self.set_text_color(255, 255, 255)
        self.cell(0, 6, '  Per-Character Memory Records', fill=True, new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0); self.ln(3)

        for name, color in [("杰洛特", COLORS["杰洛特"]), ("特莉丝", COLORS["特莉丝"]), ("兰伯特", COLORS["兰伯特"])]:
            self.set_font('C', 'B', 8); self.set_text_color(*color)
            self.cell(0, 5, f'  {name}', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)
            self.set_font('C', '', 6.5)

            acts = [t for t in trio_traces if t.get("agent") == name]
            social_targets = set(t.get("target") for t in acts if t.get("target") and t.get("target") != name)

            self.cell(0, 4, f'    Actions: {len(acts)}  |  Interacted with: {list(social_targets)}', new_x='LMARGIN', new_y='NEXT')

            # Key memories from result narratives
            results = [t for t in acts if t.get("result_narrative")]
            if results:
                for r in results:
                    self.cell(0, 4, f'    [+{r["ts"]:.0f}s] {r["result_narrative"][:130]}', new_x='LMARGIN', new_y='NEXT')
                    if r.get("result_caller_deltas"):
                        self.cell(0, 3.5, f'          deltas: {r["result_caller_deltas"]}', new_x='LMARGIN', new_y='NEXT')
            else:
                self.cell(0, 4, f'    (no resolver results captured — asyncio.run() cancelled background tasks)', new_x='LMARGIN', new_y='NEXT')

            # LLM #1 thinking samples
            thinking_samples = []
            for t in acts:
                llm = t.get("llm1_output", {})
                if isinstance(llm, dict) and llm.get("thinking"):
                    thinking_samples.append((t.get("ts", 0), llm["thinking"][:100]))
            if thinking_samples:
                self.cell(0, 4, f'    LLM #1 decision samples:', new_x='LMARGIN', new_y='NEXT')
                for ts, think in thinking_samples[:3]:
                    self.cell(0, 3.5, f'      +{ts:.0f}s: {think}', new_x='LMARGIN', new_y='NEXT')

            self.ln(2)


def build():
    pdf = PDF()

    # Storyline overview
    pdf.storyline()

    # Per-entry detail
    pdf.set_font('C', 'B', 10); pdf.set_fill_color(60, 60, 160); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 6, '  Full Timeline Detail', fill=True, new_x='LMARGIN', new_y='NEXT')
    pdf.set_text_color(0); pdf.ln(3)

    for t in trio_traces:
        pdf.entry(t)

    # Memory summary
    pdf.memory_section()

    OUT = os.path.join(PROJ, "docs", "AgentWorld_Async_Trio_Timeline.pdf")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pdf.output(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Generated: {path} ({os.path.getsize(path)} bytes)")
