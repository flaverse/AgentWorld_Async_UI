from dataclasses import dataclass, field


@dataclass
class AgentMemory:
    entries: list[dict] = field(default_factory=list)
    max_size: int = 10

    def record(self, action: str = "", target_name: str = "",
               narrative: str = "") -> None:
        self.entries.append({
            "action": action,
            "target": target_name,
            "narrative": narrative,
        })
        if len(self.entries) > self.max_size:
            self.entries.pop(0)

    def record_fail(self, action: str = "", reason: str = "") -> None:
        self.entries.append({
            "action": action,
            "result": "FAILED",
            "reason": reason,
        })
        if len(self.entries) > self.max_size:
            self.entries.pop(0)

    def recent(self, n: int = 5) -> list[dict]:
        return self.entries[-n:]

    def to_prompt_text(self, n: int = 5) -> str:
        entries = self.recent(n)
        if not entries:
            return "无"
        return "\n".join(
            f"- {e.get('action', '?')}: {e.get('narrative', e.get('reason', '?'))}"
            for e in entries
        )
