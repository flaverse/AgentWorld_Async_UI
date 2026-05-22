"""Centralized error collector for AgentWorld Async.

All errors flow through here. No silent failures anywhere.

Usage:
    from core.error_collector import errors
    errors.log_exception("brain.decide", e)
    errors.log_llm_parse_failure("brain", raw_text)
"""

from dataclasses import dataclass, field
from collections import deque
import traceback
import time
import threading


@dataclass
class ErrorRecord:
    count: int
    module: str
    message: str
    traceback_str: str
    first_at: float
    last_at: float


class ErrorCollector:
    def __init__(self, max_records: int = 200):
        self.records: deque[ErrorRecord] = deque(maxlen=max_records)
        self._lock = threading.Lock()
        self.total_errors = 0

    def _dedup_and_add(self, module: str, message: str, tb_str: str):
        with self._lock:
            self.total_errors += 1
            # Dedup: same (module, message) increments count
            key = (module, message[:120])
            for r in self.records:
                if (r.module, r.message[:120]) == key:
                    r.count += 1
                    r.last_at = time.time()
                    return
            self.records.append(ErrorRecord(
                count=1, module=module, message=message,
                traceback_str=tb_str,
                first_at=time.time(), last_at=time.time(),
            ))

    def log_exception(self, module: str, exc: Exception, context: str = ""):
        msg = f"{type(exc).__name__}: {exc}" + (f" | {context}" if context else "")
        self._dedup_and_add(module, msg, traceback.format_exc())

    def log_error(self, module: str, message: str):
        self._dedup_and_add(module, message, "")

    def log_llm_parse_failure(self, module: str, raw_text: str):
        preview = raw_text[:200].replace("\n", " ")
        self._dedup_and_add(module, f"LLM JSON parse failed. Raw: {preview}", "")


# Global singleton
errors = ErrorCollector()
