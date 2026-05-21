"""WorldClock — unified time base for the agent world.

All time parameters derive from a single measured quantity:
decision_tick — how many real seconds pass between LLM decisions.

YAML stores values as multiples of reference_tick.
WorldClock scales them to multiples of decision_tick at runtime.
"""

from dataclasses import dataclass


@dataclass
class WorldClock:
    decision_tick: float           # measured: median LLM latency × agents / concurrency
    reference_tick: float = 5.0    # DeepSeek 8-concurrent × 25-agent baseline
    max_concurrency: int = 1       # measured: final gate limit

    @property
    def scale(self) -> float:
        """Scale factor for all time-based parameters."""
        return self.reference_tick / self.decision_tick

    # ── derived intervals ──

    @property
    def poll_interval(self) -> float:
        """How often the loop ticks — same as decision_tick."""
        return self.decision_tick

    @property
    def stale_timeout(self) -> float:
        """6 cycles of inactivity = stale."""
        return 6 * self.decision_tick

    @property
    def speech_window(self) -> float:
        """Speech persists for 4 decision cycles."""
        return 4 * self.decision_tick

    @property
    def patience_default(self) -> float:
        """Default patience = 1 decision cycle."""
        return self.decision_tick

    @property
    def kl_threshold_spacing(self) -> float:
        """KL threshold spacing: typical decay over one decision cycle × 2."""
        return 2 * self.decision_tick

    # ── drive decay scaling ──

    def decay_per_tick(self, base_rate: float) -> float:
        """Convert a per-reference_tick decay rate to per-decision_tick.
        base_rate is decay per reference_tick (5s).
        Returns decay per decision_tick.
        """
        return base_rate * self.decision_tick / self.reference_tick
