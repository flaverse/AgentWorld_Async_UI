import time
from dataclasses import dataclass


class WorldClock:
    """Simulation-time clock — tracks world time progression."""
    def __init__(self, start_time_str: str, time_scale: int):
        self.time_scale = time_scale
        self.start_real = time.time()
        self.start_sim_minutes = self._parse_time(start_time_str)

    def now(self) -> float:
        elapsed_real = time.time() - self.start_real
        elapsed_sim_seconds = elapsed_real * self.time_scale
        return elapsed_sim_seconds / 60.0

    def _parse_time(self, s: str) -> float:
        h, m = map(int, s.split(":"))
        return h * 60 + m


@dataclass
class DecisionClock:
    """Decision-tick clock — calibrates world pace from observed API latency.
    All time parameters derive from a single measured quantity: decision_tick.
    """
    decision_tick: float           # measured: median LLM latency × agents / concurrency
    reference_tick: float = 5.0    # DeepSeek 8-concurrent × 25-agent baseline
    max_concurrency: int = 1

    @property
    def scale(self) -> float:
        return self.reference_tick / self.decision_tick

    @property
    def poll_interval(self) -> float:
        return self.decision_tick

    @property
    def stale_timeout(self) -> float:
        return 6 * self.decision_tick

    @property
    def speech_window(self) -> float:
        return 4 * self.decision_tick

    def decay_per_tick(self, base_rate: float) -> float:
        return base_rate * self.decision_tick / self.reference_tick
