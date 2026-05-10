import time
from dataclasses import dataclass, field


@dataclass
class Message:
    from_agent_id: str = ""
    from_agent_name: str = ""
    method: str = ""
    content: str = ""
    timestamp: float = 0.0


@dataclass
class Inbox:
    messages: list[Message] = field(default_factory=list)

    def send(self, from_id: str, from_name: str, method: str = "",
             content: str = "") -> None:
        self.messages.append(Message(
            from_agent_id=from_id,
            from_agent_name=from_name,
            method=method,
            content=content,
            timestamp=time.time(),
        ))

    def drain(self) -> list[Message]:
        msgs = self.messages.copy()
        self.messages.clear()
        return msgs

    def to_prompt_text(self) -> str:
        if not self.messages:
            return ""
        return "\n".join(
            f"- {m.from_agent_name}: \"{m.content}\""
            for m in self.messages
        )
