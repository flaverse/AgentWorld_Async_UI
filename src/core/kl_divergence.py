"""P/Q/KL 分层变化检测。四层独立: 听觉/视觉/状态/时差。
所有文本和参数从 config 注入，零硬编码。
"""
import time


def auditory_kl(p_auditory: dict, hearing: dict, text: dict) -> str:
    lines = []
    p_ids = set(p_auditory.get("speaker_ids", []))
    q_ids = {eid for eid, r in hearing.items() if r.auditory_data.get("sound")}
    for eid in q_ids - p_ids:
        lines.append(text["kl_spoke"].format(name=hearing[eid].name))
    for eid in p_ids - q_ids:
        lines.append(text["kl_left_hearing"].format(eid=eid))
    p_auditory["speaker_ids"] = list(q_ids)
    return " | ".join(lines) if lines else ""


def visual_kl(p_visual: dict, vision: dict, text: dict) -> str:
    lines = []
    p_ids = set(p_visual.get("entity_ids", []))
    q_ids = set(vision.keys())
    for eid in q_ids - p_ids:
        lines.append(text["kl_entered_vision"].format(name=vision[eid].name))
    for eid in p_ids - q_ids:
        lines.append(text["kl_left_vision"].format(eid=eid))
    for eid in q_ids & p_ids:
        old_expr = p_visual.get("expressions", {}).get(eid, "")
        new_expr = vision[eid].visual_data.get("expression", "")
        if new_expr and new_expr != old_expr:
            lines.append(text["kl_expression_changed"].format(name=vision[eid].name))
    p_visual["entity_ids"] = list(q_ids)
    p_visual["expressions"] = {eid: r.visual_data.get("expression", "") for eid, r in vision.items()}
    return " | ".join(lines) if lines else ""


def state_kl(p_state: dict, drives, currency_key: str, text: dict,
             thresholds: list = None, coin_epsilon: int = None) -> str:
    if thresholds is None: thresholds = [30, 60, 80]
    if coin_epsilon is None: coin_epsilon = 5
    lines = []
    old_drives = p_state.get("drives", {})
    new_drives = {k: round(float(v), 1) for k, v in drives.attrs.items()}
    for attr in sorted(set(old_drives) & set(new_drives)):
        ov, nv = old_drives[attr], new_drives[attr]
        for t in thresholds:
            if (ov < t <= nv) or (ov > t >= nv):
                arrow = "↑" if nv > ov else "↓"
                lines.append(text["kl_state_cross"].format(attr=attr, arrow=arrow, t=t))
                break
    old_coins = p_state.get(currency_key, 0)
    new_coins = new_drives.get(currency_key, old_coins)
    d = new_coins - old_coins
    if abs(d) >= coin_epsilon:
        sign = "+" if d > 0 else ""
        lines.append(text["kl_coin"].format(sign=sign, delta=d))
    p_state["drives"] = new_drives
    p_state[currency_key] = new_coins
    return " | ".join(lines) if lines else ""


def stale_kl(p_stale: float, text: dict, stale_timeout: int = None) -> str:
    if stale_timeout is None: stale_timeout = 30
    if time.time() - p_stale > stale_timeout:
        return text["kl_stale"]
    return ""


def total_kl(agent, sensory, drives, currency_key: str, text: dict,
             thresholds=None, coin_epsilon=None, stale_timeout=None) -> str:
    ka = auditory_kl(agent.p_auditory, sensory.hearing, text)
    kv = visual_kl(agent.p_visual, sensory.vision, text)
    ks = state_kl(agent.p_state, drives, currency_key, text, thresholds, coin_epsilon)
    kt = stale_kl(agent.p_stale, text, stale_timeout)
    return " | ".join(filter(None, [ka, kv, ks, kt]))


def snapshot_p(agent, sensory, drives, currency_key: str, text: dict,
               thresholds=None, coin_epsilon=None):
    auditory_kl(agent.p_auditory, sensory.hearing, text)
    visual_kl(agent.p_visual, sensory.vision, text)
    state_kl(agent.p_state, drives, currency_key, text, thresholds, coin_epsilon)
    agent.p_stale = time.time()
