"""TelemetryCollector — passive observation of LLM call latency.

Zero cognitive code. Records facts: how long each call took.
Provides median latency for WorldClock calibration.
"""

import time, threading, math


class TelemetryCollector:
    def __init__(self, warmup_calls: int = 20):
        self._warmup = warmup_calls
        self._lock = threading.Lock()
        self._latencies: list[float] = []       # all recorded call durations (ms)
        self._total_calls = 0
        self._total_errors = 0
        self._warmed_up = False

    def record(self, provider: str, template: str, latency_ms: float, error: bool = False):
        with self._lock:
            self._total_calls += 1
            if error:
                self._total_errors += 1
            else:
                self._latencies.append(latency_ms)
            if not self._warmed_up and self._total_calls >= self._warmup:
                self._warmed_up = True

    @property
    def warmed_up(self) -> bool:
        return self._warmed_up

    @property
    def median_latency(self) -> float:
        """Median call latency in seconds. Returns 1.5 if insufficient data."""
        with self._lock:
            if not self._latencies:
                return 1.5
            s = sorted(self._latencies)
            n = len(s)
            if n % 2 == 1:
                return s[n // 2] / 1000.0
            return (s[n // 2 - 1] + s[n // 2]) / 2000.0

    @property
    def p95_latency(self) -> float:
        with self._lock:
            if not self._latencies:
                return 3.0
            s = sorted(self._latencies)
            idx = int(len(s) * 0.95)
            return s[min(idx, len(s) - 1)] / 1000.0

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_calls": self._total_calls,
                "total_errors": self._total_errors,
                "median_ms": round(self.median_latency * 1000),
                "p95_ms": round(self.p95_latency * 1000),
                "warmed_up": self._warmed_up,
            }
