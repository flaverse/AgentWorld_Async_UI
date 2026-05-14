"""P/Q/KL 分层变化检测。听觉/视觉 — 全量 dict diff。状态/时差 — 阈值逻辑。
所有文本从 config 注入。零手工字段比较。
"""
import time


def _dicts_equal(a: dict, b: dict) -> bool:
    """Shallow dict comparison — sufficient for property-level diff."""
    return a == b


def auditory_kl(p_auditory: dict, hearing: dict, text: dict) -> str:
    """听觉 KL: 逐 entity 比较 auditory_data dict。任何 key 变化 = 信号。"""
    lines = []
    p_data = p_auditory.get("data", {})
    q_data = {eid: r.auditory_data for eid, r in hearing.items()}

    for eid in set(p_data) | set(q_data):
        pv = p_data.get(eid, {})
        qv = q_data.get(eid, {})
        if not pv and qv:
            lines.append(f"{hearing[eid].name} 开始说话")
        elif pv and not qv:
            lines.append(f"{eid} 离开听力范围")
        elif not _dicts_equal(pv, qv):
            lines.append(f"{hearing[eid].name} 声音变了")

    p_auditory["data"] = q_data
    return " | ".join(lines) if lines else ""


def visual_kl(p_visual: dict, vision: dict, text: dict) -> str:
    """视觉 KL: 逐 entity 比较 visual_data dict。任何 key 变化 = 信号。"""
    lines = []
    p_data = p_visual.get("data", {})
    q_data = {eid: r.visual_data for eid, r in vision.items()}

    for eid in set(p_data) | set(q_data):
        pv = p_data.get(eid, {})
        qv = q_data.get(eid, {})
        if not pv and qv:
            lines.append(f"{vision[eid].name} 进入视野")
        elif pv and not qv:
            lines.append(f"{eid} 离开视野")
        elif not _dicts_equal(pv, qv):
            lines.append(f"{vision[eid].name} 外观变化了")

    p_visual["data"] = q_data
    return " | ".join(lines) if lines else ""


def state_kl(p_state: dict, drives, currency_key: str, text: dict,
             thresholds: list = None, coin_epsilon: int = None) -> str:
    """状态 KL: 阈值逻辑保留。drives cross threshold / coin delta。"""
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
