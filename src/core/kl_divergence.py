"""KL Divergence Layer — P分布 vs Q分布 一阶差计算。

纯函数，零依赖。P 和 Q 是两个独立 dict。各自不感知对方存在。
只在 compute_kl() 中被比较。返回 LLM prompt 可读的变化文本。
"""


def compute_kl(p: dict, q: dict) -> str:
    """P分布 vs Q分布 = 各分量的一阶差。

    Args:
        p: P分布 — 上一步快照 {pos, zone, drives, coins, interactable, visible}
        q: Q分布 — 当前快照 (同结构)

    Returns:
        变化文本，如 "thirst ↑2 | coins -5 | 丹德里恩 进入范围 | 移动: (6,4)→(7,3)"
        无显著变化时返回空字符串
    """
    lines = []

    # ── 位置变化 ──
    p_pos = p.get("pos", [0, 0]) if p.get("pos") else [0, 0]
    q_pos = q.get("pos", [0, 0]) if q.get("pos") else [0, 0]
    dx = q_pos[0] - p_pos[0]
    dy = q_pos[1] - p_pos[1]
    if dx or dy:
        lines.append(f"移动: ({p_pos[0]},{p_pos[1]})→({q_pos[0]},{q_pos[1]})")

    # ── Zone 变化 ──
    p_zone = p.get("zone", "")
    q_zone = q.get("zone", "")
    if p_zone and q_zone and p_zone != q_zone:
        lines.append(f"zone: {p_zone}→{q_zone}")

    # ── 驱动力变化 (只显示绝对值 > 0.1) ──
    p_drives = p.get("drives", {}) or {}
    q_drives = q.get("drives", {}) or {}
    for key in sorted(set(p_drives) & set(q_drives)):
        d = q_drives[key] - p_drives[key]
        if abs(d) > 0.1:
            arrow = "↑" if d > 0 else "↓"
            lines.append(f"{key} {arrow}{abs(d):.0f}")

    # ── 金币变化 ──
    p_coins = p.get("coins", 0) or 0
    q_coins = q.get("coins", 0) or 0
    d_coins = q_coins - p_coins
    if d_coins != 0:
        sign = "+" if d_coins > 0 else ""
        lines.append(f"coins {sign}{d_coins:.0f}")

    # ── 实体进出 ──
    p_interact = set(p.get("interactable", []) or [])
    q_interact = set(q.get("interactable", []) or [])
    for name in q_interact - p_interact:
        lines.append(f"{name} 进入范围")
    for name in p_interact - q_interact:
        lines.append(f"{name} 离开范围")

    p_visible = set(p.get("visible", []) or [])
    q_visible = set(q.get("visible", []) or [])
    for name in q_visible - p_visible:
        lines.append(f"{name} 进入视野")
    for name in p_visible - q_visible:
        lines.append(f"{name} 离开视野")

    return " | ".join(lines) if lines else ""
