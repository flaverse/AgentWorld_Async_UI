import time
from dataclasses import dataclass, field


@dataclass
class AgentMemory:
    entries: list[dict] = field(default_factory=list)  # [{ts, text}]
    max_size: int = 10

    def record(self, text: str = "", ts: float = None) -> None:
        self.entries.append({
            "ts": ts if ts is not None else time.time(),
            "text": text,
        })
        if len(self.entries) > self.max_size:
            self.entries.pop(0)

    def recent(self, n: int = 5) -> list[dict]:
        return self.entries[-n:]

    def to_prompt_text(self, n: int = 5) -> str:
        entries = self.recent(n)
        if not entries:
            return "无"
        lines = []
        for e in entries:
            ts = e["ts"]
            rel = int(ts - self.entries[0]["ts"]) if self.entries else 0
            lines.append(f"[+{rel}s] {e['text']}")
        return "\n".join(lines)

    def latest(self) -> dict | None:
        return self.entries[-1] if self.entries else None
