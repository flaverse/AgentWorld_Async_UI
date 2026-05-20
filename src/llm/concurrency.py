"""Adaptive concurrency control with AIMD-like backoff.

Algorithm:
  Start:  limit = initial (default 8)
  On 429: limit = max(1, limit // 2)        — multiplicative halving
  No 429 for success_window_sec: limit += 1  — additive increase (capped at initial)

Thread-safe — works from both async and thread-pool contexts.
"""

import threading, time


class ConcurrencyGate:
    def __init__(self, initial: int = 8, success_window: float = 30.0):
        self._limit = initial
        self._initial = initial
        self._window = success_window
        self._in_flight = 0
        self._last_429_at = 0.0
        self._lock = threading.Lock()
        self._slot_available = threading.Condition(self._lock)
        self.total_429s = 0
        self.total_acquired = 0

    @property
    def limit(self) -> int:
        return self._limit

    def acquire(self):
        with self._slot_available:
            while self._in_flight >= self._limit:
                self._slot_available.wait()
            self._in_flight += 1
            self.total_acquired += 1

    def release(self):
        with self._slot_available:
            self._in_flight -= 1
            self._slot_available.notify()

    def report_429(self) -> int:
        with self._lock:
            self.total_429s += 1
            self._limit = max(1, self._limit // 2)
            self._last_429_at = time.time()
            return self._limit

    def report_ok(self):
        with self._lock:
            now = time.time()
            if now - self._last_429_at > self._window and self._limit < self._initial:
                self._limit += 1
