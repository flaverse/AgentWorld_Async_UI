"""World-level metrics: zone activity, gate usage, target_changes rate."""

from collections import Counter
from ..registry import register_metric


@register_metric(
    name="zone_activity",
    category="world",
    description="Distribution of actions across zones. Detects zone isolation.",
    source="AW built-in"
)
def zone_activity(traces: list[dict]) -> dict:
    actions = [t for t in traces if t.get("action_text")]
    if not actions:
        return {"zones": {}, "summary": "no actions"}
    counts = Counter(t.get("zone", "?") for t in actions)
    return {
        "zones": dict(counts.most_common()),
        "summary": ", ".join(f"{z}={c}" for z, c in counts.most_common()),
    }


@register_metric(
    name="gate_usage",
    category="world",
    description="Number of zone crossings (agent zone changes between consecutive traces).",
    source="AW built-in"
)
def gate_usage(traces: list[dict]) -> dict:
    crossings = 0
    crossing_agents = set()
    per_agent: dict[str, list[str]] = {}

    for t in traces:
        a = t.get("agent", "?")
        z = t.get("zone", "?")
        per_agent.setdefault(a, []).append(z)

    for a, zones in per_agent.items():
        for i in range(1, len(zones)):
            if zones[i] != zones[i-1]:
                crossings += 1
                crossing_agents.add(a)

    return {
        "total_crossings": crossings,
        "crossing_agents": sorted(crossing_agents),
        "n_crossing_agents": len(crossing_agents),
        "summary": f"{crossings} crossings by {len(crossing_agents)} agents"
        if crossings > 0 else "no crossings — gates unused",
    }


@register_metric(
    name="target_changes_rate",
    category="world",
    description="Fraction of NPC→Item interactions that produce non-empty target_changes (world mutation).",
    source="AW built-in"
)
def target_changes_rate(traces: list[dict]) -> dict:
    import json
    total = 0
    written = 0
    samples = []

    for t in traces:
        llm2 = t.get("llm2_output", "")
        if not llm2:
            continue
        total += 1
        try:
            d = json.loads(llm2)
            tc = d.get("target_changes", {})
        except Exception:
            continue
        if tc and tc != {}:
            written += 1
            if len(samples) < 5:
                samples.append({
                    "agent": t["agent"],
                    "target": t["target"],
                    "changes": tc,
                })

    rate = round(100 * written / max(total, 1), 1)
    return {
        "rate_pct": rate,
        "written": written,
        "total": total,
        "summary": f"{written}/{total} item interactions mutated world ({rate}%)",
        "samples": samples,
    }


@register_metric(
    name="concurrency_gate",
    category="world",
    description="Adaptive concurrency limit, 429 error count, and total LLM calls acquired.",
    source="AW built-in"
)
def concurrency_gate(traces: list[dict], meta: dict = None) -> dict:
    gs = (meta or {}).get("gate_stats", {})
    if not gs:
        return {"summary": "no gate stats in trace"}
    limit = gs.get("limit", 0)
    total_429s = gs.get("total_429s", 0)
    acquired = gs.get("total_acquired", 0)
    initial = gs.get("initial", 0)
    hit_ratio = round(100 * total_429s / max(acquired, 1), 1)
    diagnosis = "API 限流是主瓶颈" if total_429s > acquired * 0.3 else "KL 阈值粒度是主瓶颈" if acquired < 100 else "平衡"
    return {
        "initial_limit": initial,
        "final_limit": limit,
        "total_429s": total_429s,
        "total_acquired": acquired,
        "429_ratio_pct": hit_ratio,
        "summary": f"limit={limit}, {total_429s}×429 / {acquired} calls ({hit_ratio}%) → {diagnosis}",
    }
