"""Evaluation runner. Reads a trace JSON, runs all registered metrics."""

import json

from .registry import REGISTRY
from .report import EvalReport


def run_eval(trace_path: str) -> EvalReport:
    with open(trace_path) as f:
        traces: list[dict] = json.load(f)

    actions = [t for t in traces if t.get("action_text")]
    agents = sorted(set(t["agent"] for t in traces))

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for name, meta in REGISTRY.items():
        try:
            results[name] = {
                "value": meta["fn"](traces),
                "category": meta["category"],
                "description": meta["description"],
                "source": meta["source"],
            }
        except Exception as e:
            errors[name] = f"{type(e).__name__}: {e}"

    return EvalReport(
        trace_path=trace_path,
        n_traces=len(traces),
        n_actions=len(actions),
        n_agents=len(agents),
        agents=agents,
        results=results,
        errors=errors,
    )
