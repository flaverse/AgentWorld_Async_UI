"""AgentKnowledge: 三层知识发现 —— 亲身(1.0) / 观察(0.3-0.7) / 未知(0)。

原则 ⑦ Agent 自治: 知识是 Agent 私有的。不同 Agent 对同一实体可能有不同认知。
原则 ④ 配置即行为: knowledge_db 由交互结果自动填充，不由 YAML 预设。
"""
from dataclasses import dataclass, field


@dataclass
class InterfaceKnowledge:
    entity_id: str = ""
    entity_name: str = ""
    action: str = ""
    description: str | None = None
    experienced_deltas: dict | None = None
    confidence: float = 0.0
    source: str = ""            # "direct" | "observed"


@dataclass
class AgentKnowledge:
    entries: dict[str, InterfaceKnowledge] = field(default_factory=dict)

    def _key(self, entity_id: str, action: str) -> str:
        return f"{entity_id}::{action}"

    def learn_direct(self, entity_id: str, entity_name: str,
                     action: str, narrative: str,
                     caller_deltas: dict | None = None) -> None:
        """亲身经历 → 完整认知 (confidence 1.0)。"""
        key = self._key(entity_id, action)
        self.entries[key] = InterfaceKnowledge(
            entity_id=entity_id, entity_name=entity_name,
            action=action, description=narrative,
            experienced_deltas=caller_deltas,
            confidence=1.0, source="direct",
        )

    def learn_observed(self, entity_id: str, entity_name: str,
                       action: str) -> None:
        """观察他人 → 模糊认知 (confidence 0.3→0.7)。"""
        key = self._key(entity_id, action)
        if key not in self.entries:
            self.entries[key] = InterfaceKnowledge(
                entity_id=entity_id, entity_name=entity_name,
                action=action, confidence=0.3, source="observed",
            )
        else:
            existing = self.entries[key]
            if existing.source == "observed":
                existing.confidence = min(0.7, existing.confidence + 0.2)

    def get_known(self, entity_id: str) -> list[InterfaceKnowledge]:
        return [e for e in self.entries.values()
                if e.entity_id == entity_id and e.confidence > 0]

    def get_known_actions(self, entity_id: str) -> dict[str, float]:
        """返回 {action_name: confidence}。"""
        return {e.action: e.confidence
                for e in self.get_known(entity_id)}
