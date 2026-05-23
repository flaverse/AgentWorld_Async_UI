"""Concurrent agent execution and trace collection."""
import time
import asyncio
from collections import defaultdict
from datetime import datetime
from loop import run_agent


async def run_concurrent(agents, world, brain, assembler, systems,
                         runtime: float, cfg,
                         *, trace_fn=None, director=None,
                         dashboard_emit=None):
    """Run all agents concurrently."""
    tasks = [run_agent(a, world, brain, assembler, systems,
                       runtime, trace_fn=trace_fn, cfg=cfg,
                       director=director, dashboard_emit=dashboard_emit)
             for a in agents]
    await asyncio.gather(*tasks, return_exceptions=True)


class TraceCollector:
    """Collect and merge traces from concurrent agent runs."""

    def __init__(self):
        self.start_time = time.time()
        self._traces: dict[str, list] = defaultdict(list)
        self._meta: dict = {}

    def set_meta(self, meta: dict):
        self._meta = meta

    def callback(self):
        """Return a trace_fn suitable for run_agent()."""
        collector = self

        def fn(trace):
            trace["ts"] = time.time() - collector.start_time
            trace["wall"] = datetime.now().isoformat()
            collector._traces[trace["agent"]].append(trace)
        return fn

    def merged(self) -> list[dict]:
        traces = [t for per_agent in self._traces.values() for t in per_agent]
        traces.sort(key=lambda t: t.get("ts", 0))
        if self._meta:
            traces.insert(0, {"_meta": self._meta, "agent": "_meta", "ts": 0})
        return traces

    def save(self, path: str):
        import json
        with open(path, "w") as f:
            json.dump(self.merged(), f, ensure_ascii=False, indent=2)
