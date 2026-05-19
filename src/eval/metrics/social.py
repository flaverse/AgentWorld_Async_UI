"""Social network metrics: degree centrality, reciprocity, interaction density."""

from ..registry import register_metric


@register_metric(
    name="degree_centrality",
    category="social",
    description="Number of unique interaction partners per agent. Mean reflects social density.",
    source="OASIS 2024"
)
def degree_centrality(traces: list[dict]) -> dict:
    partners: dict[str, set[str]] = {}
    for t in traces:
        if not t.get("action_text"):
            continue
        a, b = t["agent"], t["target"]
        partners.setdefault(a, set()).add(b)
        partners.setdefault(b, set()).add(a)
    if not partners:
        return {"mean": 0, "max": 0, "summary": "no interactions"}
    per = {a: len(p) for a, p in partners.items()}
    mean = round(sum(per.values()) / len(per), 1)
    return {
        "mean": mean,
        "max": max(per.values()),
        "min": min(per.values()),
        "summary": f"mean={mean} partners/agent",
        "per_agent": dict(sorted(per.items(), key=lambda x: -x[1])),
    }


@register_metric(
    name="reciprocity_rate",
    category="social",
    description="Fraction of conversation edges that are bidirectional (A↔B, not just A→B).",
    source="Social Simulacra 2022"
)
def reciprocity_rate(traces: list[dict]) -> dict:
    edges: dict[tuple, int] = {}
    for t in traces:
        if t.get("llm2_prompt"):
            continue
        key = (t["agent"], t["target"])
        edges[key] = edges.get(key, 0) + 1
    if not edges:
        return {"rate": 0, "summary": "no edges"}
    bidirectional = sum(1 for (a, b) in edges if (b, a) in edges)
    total_pairs = len(set(tuple(sorted(k)) for k in edges))
    rate = round(100 * bidirectional / max(total_pairs, 1), 1)
    return {
        "rate_pct": rate,
        "bidirectional": bidirectional,
        "total_pairs": total_pairs,
        "summary": f"{rate}% bidirectional ({bidirectional}/{total_pairs})",
    }


@register_metric(
    name="interaction_density",
    category="social",
    description="Average actions per agent per second of simulated time.",
    source="OASIS 2024"
)
def interaction_density(traces: list[dict]) -> dict:
    agents = sorted(set(t["agent"] for t in traces if t.get("action_text")))
    if not agents:
        return {"density": 0, "summary": "no agents"}
    n_actions = sum(1 for t in traces if t.get("action_text"))
    # Estimate duration from trace timestamps
    timestamps = [t.get("ts", 0) for t in traces if t.get("action_text")]
    if not timestamps or len(timestamps) < 2:
        duration = 1
    else:
        duration = max(timestamps) - min(timestamps)
        if duration < 1:
            duration = 1
    density = round(n_actions / (len(agents) * duration), 3)
    return {
        "density": density,
        "n_actions": n_actions,
        "n_agents": len(agents),
        "duration_s": round(duration, 1),
        "summary": f"{density} acts/agent/s",
    }
