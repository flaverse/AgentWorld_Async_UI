"""World-level metrics: zone activity, gate usage, target_changes rate."""

from collections import Counter
from ..registry import register_metric


@register_metric(
    name="zone_activity",
    category="world",
    description="Distribution of actions across zones. Detects zone isolation."
              " Formula: Count(t.zone) for t∈T with action_text.",
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
    description="Number of zone crossings (agent zone changes between consecutive traces)."
              " Formula: Σ_{a∈A} |{i: zone_i(a) ≠ zone_{i-1}(a)}|.",
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
    description="Fraction of NPC→Item interactions that produce non-empty target_changes (world mutation)."
              " Formula: |{t∈T: t.target_changes ≠ {} AND t is NPC→Item}| / |NPC→Item actions|.",
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
    gs_all = (meta or {}).get("gate_stats", {})
    if not gs_all:
        return {"summary": "no gate stats in trace"}
    # Multi-provider: aggregate
    total_429s = sum(g.get("total_429s", 0) for g in gs_all.values())
    total_acquired = sum(g.get("total_acquired", 0) for g in gs_all.values())
    per_provider = {}
    for pname, g in gs_all.items():
        acquired = g.get("total_acquired", 0)
        hit_ratio = round(100 * g.get("total_429s", 0) / max(acquired, 1), 1)
        per_provider[pname] = f"limit={g.get('limit')} 429s={g.get('total_429s')}/{acquired} ({hit_ratio}%)"
    global_ratio = round(100 * total_429s / max(total_acquired, 1), 1)
    diagnosis = "API 限流是主瓶颈" if total_429s > total_acquired * 0.3 else "API 延迟是主瓶颈"
    return {
        "total_429s": total_429s,
        "total_acquired": total_acquired,
        "global_429_pct": global_ratio,
        "per_provider": per_provider,
        "summary": f"acquired={total_acquired}, 429s={total_429s} ({global_ratio}%) → {diagnosis}",
    }
