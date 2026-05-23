"""Narrative quality metrics: conversation depth, thread persistence, completion rate."""

from collections import defaultdict
from ..registry import register_metric


@register_metric(
    name="conversation_depth",
    category="narrative",
    description="Distribution of multi-turn conversation chain lengths. Detects if agents sustain dialogue."
              " Formula: chain = (a1→b1, a2→b2, ...) where a_{k+1}=b_k and Δt<20s.",
    source="Generative Agents 2023"
)
def conversation_depth(traces: list[dict]) -> dict:
    actions = [t for t in traces if t.get("action_text") and not t.get("llm2_prompt")]
    actions.sort(key=lambda x: x.get("ts", 0))

    chains = []
    current = []
    for t in actions:
        a, b, ts = t["agent"], t["target"], t.get("ts", 0)
        if not current:
            current = [(a, b, ts)]
        else:
            last_a, last_b, last_ts = current[-1]
            if (a, b) == (last_b, last_a) and (ts - last_ts) < 20:
                current.append((a, b, ts))
            else:
                if len(current) >= 2:
                    chains.append(current)
                current = [(a, b, ts)]
    if len(current) >= 2:
        chains.append(current)

    if not chains:
        return {"max_depth": 0, "mean_depth": 0, "summary": "no multi-turn conversations"}

    depths = [len(c) for c in chains]
    max_depth = max(depths)
    mean_depth = round(sum(depths) / len(depths), 1)
    dist = {}
    for d in depths:
        dist[d] = dist.get(d, 0) + 1

    return {
        "n_chains": len(chains),
        "max_depth": max_depth,
        "mean_depth": mean_depth,
        "depth_distribution": {str(k): v for k, v in sorted(dist.items())},
        "summary": f"{len(chains)} chains, max={max_depth} turns, mean={mean_depth}",
    }


@register_metric(
    name="thread_persistence",
    category="narrative",
    description="Average duration (seconds) an agent maintains the same main_thread before changing it."
              " Formula: mean duration between consecutive thread_text changes, computed per agent.",
    source="AW built-in"
)
def thread_persistence(traces: list[dict]) -> dict:
    agent_threads: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for t in traces:
        llm1 = t.get("llm1_output")
        if isinstance(llm1, dict) and llm1.get("main_thread"):
            agent_threads[t["agent"]].append((t.get("ts", 0), llm1["main_thread"]))

    durations = []
    per_agent_avg = {}
    for a, seq in agent_threads.items():
        if len(seq) < 2:
            continue
        seq.sort()
        run_start = seq[0][0]
        run_len = 0
        for i in range(1, len(seq)):
            if seq[i][1] == seq[i-1][1]:
                continue
            durations.append(seq[i-1][0] - run_start)
            run_start = seq[i][0]
        durations.append(seq[-1][0] - run_start)
        if durations:
            per_agent_avg[a] = round(sum(durations) / len(durations), 1)

    if not durations:
        return {"avg_duration_s": 0, "summary": "no thread data"}

    avg = round(sum(durations) / len(durations), 1)
    return {
        "avg_duration_s": avg,
        "max_duration_s": round(max(durations), 1),
        "n_thread_changes": len(durations),
        "summary": f"avg {avg}s per thread, {per_agent_avg}",
    }


@register_metric(
    name="main_thread_completion_rate",
    category="narrative",
    description="Fraction of main_threads where agent explicitly marked thread_completed=true.",
    source="AW built-in"
)
def main_thread_completion_rate(traces: list[dict]) -> dict:
    threads_seen = set()
    completed = 0
    for t in traces:
        llm1 = t.get("llm1_output")
        if not isinstance(llm1, dict):
            continue
        mt = llm1.get("main_thread")
        if not mt:
            continue
        threads_seen.add(str(mt)[:80])
        if t.get("thread_completed"):
            completed += 1

    return {
        "unique_threads": len(threads_seen),
        "completions_observed": completed,
        "rate_pct": round(100 * completed / max(len(threads_seen), 1), 1),
        "summary": f"{completed}/{len(threads_seen)} threads completed ({100*completed//max(len(threads_seen),1)}%)",
    }
