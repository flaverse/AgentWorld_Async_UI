"""P/Q/KL 分层变化检测。
四层独立: 听觉/视觉/状态/时差。每层维护自己的 P 快照。
所有可配置参数通过 simulation config 传入，无硬编码。
"""
import time

# ── Defaults (overridable via world.yaml simulation section) ──
DEFAULT_THRESHOLDS = [30, 60, 80]
DEFAULT_COIN_EPSILON = 5
DEFAULT_STALE_TIMEOUT = 30


def auditory_kl(p_auditory: dict, hearing: dict) -> str:
    """听觉 KL: speaker_ids 变化 → 有人说了新的 / 离开听力范围"""
    lines = []
    p_ids = set(p_auditory.get("speaker_ids", []))
    q_ids = {eid for eid, r in hearing.items() if r.auditory_data.get("sound")}
    for eid in q_ids - p_ids:
        lines.append(f"{hearing[eid].name} 说话了")
    for eid in p_ids - q_ids:
        lines.append(f"{eid} 离开听力范围")
    p_auditory["speaker_ids"] = list(q_ids)
    return " | ".join(lines) if lines else ""


def visual_kl(p_visual: dict, vision: dict) -> str:
    """视觉 KL: 实体进出 / 表情变化"""
    lines = []
    p_ids = set(p_visual.get("entity_ids", []))
    q_ids = set(vision.keys())
    for eid in q_ids - p_ids:
        lines.append(f"{vision[eid].name} 进入视野")
    for eid in p_ids - q_ids:
        lines.append(f"{eid} 离开视野")
    for eid in q_ids & p_ids:
        old_expr = p_visual.get("expressions", {}).get(eid, "")
        new_expr = vision[eid].visual_data.get("expression", "")
        if new_expr and new_expr != old_expr:
            lines.append(f"{vision[eid].name} 表情变了")
    p_visual["entity_ids"] = list(q_ids)
    p_visual["expressions"] = {eid: r.visual_data.get("expression", "") for eid, r in vision.items()}
    return " | ".join(lines) if lines else ""


def state_kl(p_state: dict, drives, coins: float,
             thresholds: list = None, coin_epsilon: int = None) -> str:
    """状态 KL: 仅当 cross 阈值时返回。hysteresis 防 drift 反复触发。"""
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    if coin_epsilon is None:
        coin_epsilon = DEFAULT_COIN_EPSILON

    lines = []
    old_drives = p_state.get("drives", {})
    new_drives = {k: round(float(v), 1) for k, v in drives.attrs.items()}
    for attr in sorted(set(old_drives) & set(new_drives)):
        ov, nv = old_drives[attr], new_drives[attr]
        for t in thresholds:
            if (ov < t <= nv) or (ov > t >= nv):
                arrow = "↑" if nv > ov else "↓"
                lines.append(f"{attr} {arrow}突破{t}")
                break
    old_coins = p_state.get("coins", 0)
    if abs(coins - old_coins) >= coin_epsilon:
        sign = "+" if coins > old_coins else ""
        lines.append(f"coins {sign}{coins - old_coins:.0f}")
    p_state["drives"] = new_drives
    p_state["coins"] = coins
    return " | ".join(lines) if lines else ""


def stale_kl(p_stale: float, stale_timeout: int = None) -> str:
    """时差 KL: 超过 stale_timeout 秒无 decide → 触发"""
    if stale_timeout is None:
        stale_timeout = DEFAULT_STALE_TIMEOUT
    if time.time() - p_stale > stale_timeout:
        return "太久没事做了"
    return ""


def total_kl(agent, sensory, drives, coins,
             thresholds=None, coin_epsilon=None, stale_timeout=None) -> str:
    """四通道并集。非空 → trigger decide。空 → continue observing。"""
    ka = auditory_kl(agent.p_auditory, sensory.hearing)
    kv = visual_kl(agent.p_visual, sensory.vision)
    ks = state_kl(agent.p_state, drives, coins, thresholds, coin_epsilon)
    kt = stale_kl(agent.p_stale, stale_timeout)
    return " | ".join(filter(None, [ka, kv, ks, kt]))


def snapshot_p(agent, sensory, drives, coins,
               thresholds=None, coin_epsilon=None):
    """更新所有 KL 通道的 P 快照"""
    auditory_kl(agent.p_auditory, sensory.hearing)
    visual_kl(agent.p_visual, sensory.vision)
    state_kl(agent.p_state, drives, coins, thresholds, coin_epsilon)
    agent.p_stale = time.time()
