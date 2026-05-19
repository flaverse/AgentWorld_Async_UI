"""Drive system metrics: convergence, delta alignment, mood trajectory."""

from collections import defaultdict
from ..registry import register_metric


@register_metric(
    name="delta_alignment",
    category="drive",
    description="Fraction of self_deltas that move drives toward satisfaction (reduce high >50, boost low <30).",
    source="AW built-in"
)
def delta_alignment(traces: list[dict]) -> dict:
    actions = [t for t in traces if t.get("action_text")]
    aligned, total = 0, 0
    per_agent_align: dict[str, list[float]] = defaultdict(list)

    for t in actions:
        llm1 = t.get("llm1_output")
        if not isinstance(llm1, dict):
            continue
        sd = llm1.get("self_deltas", {})
        drives = t.get("drives", {})
        if not sd or not drives:
            continue
        for attr, delta in sd.items():
            if attr == "coins" or attr not in drives:
                continue
            val = drives.get(attr, 50)
            if (val > 50 and delta < 0) or (val < 30 and delta > 0):
                aligned += 1
            total += 1
            a = t["agent"]
            per_agent_align[a].append(1 if (val > 50 and delta < 0) or (val < 30 and delta > 0) else 0)

    rate = round(100 * aligned / max(total, 1), 1)
    per = {a: round(100 * sum(vals) / len(vals), 1) for a, vals in per_agent_align.items()}
    return {
        "rate_pct": rate,
        "aligned": aligned,
        "total": total,
        "summary": f"{rate}% delta-drive alignment ({aligned}/{total})",
        "per_agent": dict(sorted(per.items(), key=lambda x: x[1])[:10]),
    }


@register_metric(
    name="drive_convergence",
    category="drive",
    description="Net change in each drive attribute from first to last snapshot. Negative = drives being satisfied.",
    source="AW built-in"
)
def drive_convergence(traces: list[dict]) -> dict:
    per_agent: dict[str, list[tuple[float, dict]]] = defaultdict(list)
    for t in traces:
        d = t.get("drives", {})
        if d:
            per_agent[t["agent"]].append((t.get("ts", 0), d))

    net_changes: dict[str, float] = defaultdict(float)
    for a, snapshots in per_agent.items():
        if len(snapshots) < 2:
            continue
        snapshots.sort()
        first = snapshots[0][1]
        last = snapshots[-1][1]
        for k in first:
            net_changes[k] += last.get(k, 0) - first.get(k, 0)

    n = len(per_agent)
    avg_changes = {k: round(v / max(n, 1), 1) for k, v in net_changes.items()}

    # Summarize: overall trend per drive
    trends = {}
    for k, v in avg_changes.items():
        if v < -5:
            trends[k] = "↓ satisfied"
        elif v > 5:
            trends[k] = "↑ increasing"
        else:
            trends[k] = "~ stable"

    return {
        "avg_net_change": avg_changes,
        "trends": trends,
        "summary": ", ".join(f"{k}={v} ({trends[k]})" for k, v in avg_changes.items()),
    }


@register_metric(
    name="mood_trajectory",
    category="drive",
    description="Average mood change across all agents from first to last snapshot.",
    source="AW built-in"
)
def mood_trajectory(traces: list[dict]) -> dict:
    per_agent: dict[str, list[float]] = defaultdict(list)
    for t in traces:
        d = t.get("drives", {})
        mood = d.get("mood")
        if mood is not None:
            per_agent[t["agent"]].append(mood)

    deltas = []
    for a, moods in per_agent.items():
        if len(moods) >= 2:
            deltas.append(moods[-1] - moods[0])

    if not deltas:
        return {"avg_delta": 0, "summary": "no mood data"}

    avg = round(sum(deltas) / len(deltas), 1)
    improving = sum(1 for d in deltas if d > 0)
    return {
        "avg_mood_delta": avg,
        "agents_improving": f"{improving}/{len(deltas)}",
        "summary": f"avg mood change={avg:+} ({improving}/{len(deltas)} improved)",
    }
