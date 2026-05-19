"""AgentWorld Async — Evaluation Module.

Completely decoupled from engine code. Zero src/ imports.
Reads a trace JSON file, runs all registered metrics, produces EvalReport.

Usage:
    from eval import run_eval
    report = run_eval("trace.json")
    print(report.to_table())
    report.save("eval_result.json")
"""

from .runner import run_eval     # noqa: F401
from .report import EvalReport   # noqa: F401
from . import metrics            # noqa: F401  trigger @register_metric on all metric modules
