"""P/Q 分层变化检测。全 channel 通用 dict diff。状态/时差 — 阈值逻辑。
所有文本从 config 注入。零手工字段比较。
"""
import time


def _extract_data(val) -> dict:
    """Extract .data dict from SensorRecord or dict, uniformly."""
    if val is None:
        return {}
    if hasattr(val, 'data'):
        return val.data or {}
    if isinstance(val, dict):
        return val.get("data", {})
    return {}


def channel_delta(channel_name: str, p_data: dict, q_data: dict,
                  records: dict, text: dict) -> str:
    """通用 channel diff: 逐 entity 比较 data dict。任何 key 变化 = 信号。"""
    lines = []
    for eid in set(p_data) | set(q_data):
        pv = _extract_data(p_data.get(eid))
        qv = _extract_data(q_data.get(eid))
        name = records.get(eid, eid)
        if not pv and qv:
            lines.append(text["kl_entered"].format(channel=channel_name, name=name))
        elif pv and not qv:
            lines.append(text["kl_left"].format(channel=channel_name, name=name))
        elif pv != qv:
            lines.append(text["kl_changed"].format(channel=channel_name, name=name))
    return " | ".join(lines) if lines else ""


def state_delta(p_state: dict, drives, currency_key: str, text: dict,
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


def stale_check(p_stale: float, text: dict, stale_timeout: int = None) -> str:
    if stale_timeout is None: stale_timeout = 30
    if time.time() - p_stale > stale_timeout:
        return text["kl_stale"].format(stale_timeout=stale_timeout)
    return ""


def total_delta(agent_layer, sensory, drives, currency_key: str, text: dict,
                thresholds=None, coin_epsilon=None, stale_timeout=None) -> str:
    """遍历 sensory.channels 所有层，逐层 channel_delta。每轮用浅拷贝更新 P。"""
    parts = []
    for ch_name, ch_data in sensory.channels.items():
        if not ch_data:
            continue
        delta = channel_delta(ch_name,
                              agent_layer.p_channels.get(ch_name, {}),
                              ch_data,
                              {eid: r.name for eid, r in ch_data.items()},
                              text)
        if delta:
            parts.append(delta)
        agent_layer.p_channels[ch_name] = dict(ch_data)
    ks = state_delta(agent_layer.p_state, drives, currency_key, text, thresholds, coin_epsilon)
    if ks: parts.append(ks)
    kt = stale_check(agent_layer.p_stale, text, stale_timeout)
    if kt: parts.append(kt)
    return " | ".join(parts)


def snapshot_p(agent_layer, sensory, drives, currency_key: str, text: dict,
               thresholds=None, coin_epsilon=None):
    state_delta(agent_layer.p_state, drives, currency_key, text, thresholds, coin_epsilon)
    agent_layer.p_stale = time.time()
