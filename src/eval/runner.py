"""Evaluation runner. Reads a trace JSON, runs all registered metrics."""

import json

from .registry import REGISTRY
from .report import EvalReport


def run_eval(trace_path: str) -> EvalReport:
    with open(trace_path) as f:
        traces: list[dict] = json.load(f)

    # Extract _meta if embedded (gate stats, etc.)
    meta = {}
    if traces and isinstance(traces[0], dict) and traces[0].get("_meta"):
        meta = traces.pop(0)["_meta"]

    actions = [t for t in traces if t.get("action_text")]
    agents = sorted(set(t["agent"] for t in traces))

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for name, m in REGISTRY.items():
        try:
            fn = m["fn"]
            # Inject meta as second arg if function accepts it
            import inspect
            sig = inspect.signature(fn)
            if len(sig.parameters) > 1 and meta:
                results[name] = {
                    "value": fn(traces, meta),
                    "category": m["category"],
                    "description": m["description"],
                    "source": m["source"],
                }
            else:
                results[name] = {
                    "value": fn(traces),
                    "category": m["category"],
                    "description": m["description"],
                    "source": m["source"],
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
