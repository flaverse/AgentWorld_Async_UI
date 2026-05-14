import time
from dataclasses import dataclass, field


_DEFAULT_LABELS = {
    "empty_memory": "无",
    "memory_entry": "[+{rel}s] {text}",
}


@dataclass
class AgentMemory:
    entries: list[dict] = field(default_factory=list)  # [{ts, text}]
    max_size: int = 10

    def record(self, text: str = "", ts: float = None) -> None:
        self.entries.append({
            "ts": ts if ts is not None else time.time(),
            "text": text,
        })
        non_pinned = [e for e in self.entries if not e.get("pinned")]
        while len(non_pinned) > self.max_size:
            idx = self.entries.index(non_pinned[0])
            self.entries.pop(idx)
            non_pinned.pop(0)

    def recent(self, n: int = 5) -> list[dict]:
        return self.entries[-n:]

    def to_prompt_text(self, n: int = 5, labels: dict = None) -> str:
        if labels is None:
            labels = _DEFAULT_LABELS
        entries = self.recent(n)
        if not entries:
            return labels["empty_memory"]
        lines = []
        for e in entries:
            ts = e["ts"]
            rel = int(ts - self.entries[0]["ts"]) if self.entries else 0
            lines.append(labels["memory_entry"].format(rel=rel, text=e['text']))
        return "\n".join(lines)

    def latest(self) -> dict | None:
        return self.entries[-1] if self.entries else None

    def pin(self, text: str = ""):
        """Add a pinned entry that won't be evicted by max_size limit."""
        self.entries.append({"ts": time.time(), "text": text, "pinned": True})
