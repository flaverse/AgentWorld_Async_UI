"""Drive system metrics: convergence, mood trajectory, final state health."""

from collections import defaultdict
from ..registry import register_metric


@register_metric(
    name="final_drive_health",
    category="drive",
    description="Final attribute values per agent classified as ok(0-50) / high(50-80) / extreme(80+)."
              " Formula: per-agent classification of last snapshot's drive values against fixed thresholds.",
    source="AW built-in"
)
def final_drive_health(traces: list[dict]) -> dict:
    per_agent: dict[str, list[tuple[float, dict]]] = defaultdict(list)
    for t in traces:
        d = t.get("drives", {})
        if d:
            per_agent[t["agent"]].append((t.get("ts", 0), d))

    final_snapshots: dict[str, dict] = {}
    for a, snapshots in per_agent.items():
        if snapshots:
            snapshots.sort()
            final_snapshots[a] = snapshots[-1][1]

    # Classify each attribute per agent
    status_counts: dict[str, int] = {"ok": 0, "high": 0, "extreme": 0}
    per_agent_detail = {}
    for a, drives in final_snapshots.items():
        agent_status = {}
        for attr, val in drives.items():
            if attr == "coins":
                continue
            if 0 <= val <= 50:
                tag = "ok"
            elif 50 < val <= 80:
                tag = "high"
            else:
                tag = "extreme"
            status_counts[tag] += 1
            agent_status[attr] = f"{val:.0f}"
        per_agent_detail[a] = agent_status

    total = sum(status_counts.values())
    return {
        "per_agent": per_agent_detail,
        "distribution": {k: f"{v}/{total}" for k, v in status_counts.items()},
        "summary": f"{status_counts['ok']} ok, {status_counts['high']} high, {status_counts['extreme']} extreme",
    }


@register_metric(
    name="drive_convergence",
    category="drive",
    description="Net change in each drive attribute from first to last snapshot."
              " Formula: (1/n) · Σ_{a∈A} (drive_k^last(a) - drive_k^first(a)).",
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
    description="Average mood change across all agents from first to last snapshot."
              " Formula: (1/n) · Σ_{a∈A} (mood_last(a) - mood_first(a)).",
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
