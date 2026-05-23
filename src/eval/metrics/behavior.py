"""Behavior metrics: action diversity, dialogue rate, repetition, NPC ratios."""

from collections import Counter
from ..registry import register_metric


@register_metric(
    name="action_diversity",
    category="behavior",
    description="Fraction of unique action texts among all actions. Higher = less repetitive."
              " Formula: diversity = |unique(actions)| / |actions|.",
    source="AW built-in"
)
def action_diversity(traces: list[dict]) -> dict:
    actions = [t.get("action_text", "") for t in traces if t.get("action_text")]
    if not actions:
        return {"rate_pct": 0, "summary": "no actions"}
    unique = len(set(actions))
    rate = round(100 * unique / len(actions), 1)
    top = Counter(actions).most_common(3)
    return {
        "rate_pct": rate,
        "unique": unique,
        "total": len(actions),
        "summary": f"{rate}% unique ({unique}/{len(actions)})",
        "most_repeated": [{"action": a[:80], "count": c} for a, c in top],
    }


@register_metric(
    name="dialogue_rate",
    category="behavior",
    description="Fraction of actions with spoken dialogue."
              " Formula: |{t∈T: t.llm1_output.dialogue ≠ null}| / |T|.",
    source="AW built-in"
)
def dialogue_rate(traces: list[dict]) -> dict:
    actions = [t for t in traces if t.get("action_text")]
    if not actions:
        return {"rate_pct": 0, "summary": "no actions"}
    with_dialogue = 0
    for t in actions:
        llm1 = t.get("llm1_output")
        if isinstance(llm1, dict) and llm1.get("dialogue"):
            with_dialogue += 1
    rate = round(100 * with_dialogue / len(actions), 1)
    return {
        "rate_pct": rate,
        "with_dialogue": with_dialogue,
        "total_actions": len(actions),
        "summary": f"{rate}% dialogue ({with_dialogue}/{len(actions)})",
    }


@register_metric(
    name="repetition_rate",
    category="behavior",
    description="Fraction of consecutive identical actions. Lower = more spontaneous."
              " Formula: |{i: action_i = action_{i-1}}| / (|actions| - 1).",
    source="AW built-in"
)
def repetition_rate(traces: list[dict]) -> dict:
    agent_acts: dict[str, list[str]] = {}
    for t in traces:
        if not t.get("action_text"):
            continue
        agent_acts.setdefault(t["agent"], []).append(t.get("action_text", ""))

    total, repeats = 0, 0
    per_agent = {}
    for a, acts in agent_acts.items():
        r = sum(1 for i in range(1, len(acts)) if acts[i] == acts[i-1])
        total += len(acts) - 1 if len(acts) > 1 else 0
        repeats += r
        if len(acts) > 1:
            per_agent[a] = round(100 * r / (len(acts) - 1), 1)

    rate = round(100 * repeats / max(total, 1), 1)
    return {
        "rate_pct": rate,
        "repeats": repeats,
        "total_pairs": total,
        "summary": f"{rate}% adjacent repetition",
        "per_agent": dict(sorted(per_agent.items(), key=lambda x: -x[1])),
    }


@register_metric(
    name="npc_interaction_ratio",
    category="behavior",
    description="Fraction of actions that are NPC↔NPC vs NPC→Item."
              " Formula: |{t∈T: t.llm2_prompt = null}| / |T|.",
    source="AW built-in"
)
def npc_interaction_ratio(traces: list[dict]) -> dict:
    actions = [t for t in traces if t.get("action_text")]
    if not actions:
        return {"npc_npc_pct": 0, "summary": "no actions"}
    npc = sum(1 for t in actions if not t.get("llm2_prompt"))
    itm = len(actions) - npc
    return {
        "npc_npc": npc,
        "npc_item": itm,
        "npc_npc_pct": round(100 * npc / len(actions), 1),
        "summary": f"{100*npc//len(actions)}% NPC↔NPC ({npc}/{len(actions)})",
    }


@register_metric(
    name="per_agent_activity",
    category="behavior",
    description="Action count per agent. Identifies over/under-active agents.",
    source="AW built-in"
)
def per_agent_activity(traces: list[dict]) -> dict:
    counts = Counter(t["agent"] for t in traces if t.get("action_text"))
    if not counts:
        return {"mean": 0, "summary": "no activity"}
    vals = list(counts.values())
    mean = round(sum(vals) / len(vals), 1)
    return {
        "mean": mean,
        "max": max(vals),
        "min": min(vals),
        "std_dev": round(_std_dev(vals), 1),
        "summary": f"mean={mean} acts/agent, range=[{min(vals)}, {max(vals)}]",
        "per_agent": dict(counts.most_common()),
    }


@register_metric(
    name="null_action_rate",
    category="behavior",
    description="Fraction of cycles where the agent chose to idle (action=null)."
              " Formula: |{t∈T: t.action_text = null}| / |T|.",
    source="AW built-in"
)
def null_action_rate(traces: list[dict]) -> dict:
    total = len(traces)
    if total == 0:
        return {"rate_pct": 0, "summary": "no traces"}
    nulls = sum(1 for t in traces if not t.get("action_text"))
    return {
        "rate_pct": round(100 * nulls / total, 1),
        "nulls": nulls,
        "total": total,
        "summary": f"{100*nulls//max(total,1)}% null ({nulls}/{total})",
    }


def _std_dev(vals: list) -> float:
    if len(vals) < 2:
        return 0
    mean = sum(vals) / len(vals)
    return (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
