from dataclasses import dataclass, field
from enum import Enum
from layers.base import Layer


class TargetType(str, Enum):
    PASSIVE = "passive"
    AGENT = "agent"


class ResolveType(str, Enum):
    RULE = "rule"
    LLM = "llm"


@dataclass
class ActionDef:
    method: str = ""
    target_type: TargetType = TargetType.PASSIVE
    resolve: ResolveType = ResolveType.RULE
    params: dict = field(default_factory=dict)
    rule: dict | None = None
    estimated_duration: int = 5


@dataclass
class InteractionLayer(Layer):
    interaction_radius: int = 2
    public_attrs: dict = field(default_factory=dict)
    private_attrs: dict = field(default_factory=dict)
    actions: dict[str, ActionDef] = field(default_factory=dict)

    def interact(self, action: str | None = None) -> list[str]:
        if action is None:
            return list(self.actions.keys())
        raise NotImplementedError("execute via InteractionSystem")

    def get_action(self, action: str) -> ActionDef | None:
        return self.actions.get(action)

    def apply_deltas(self, deltas: dict) -> None:
        for key, delta in deltas.items():
            self.private_attrs[key] = self.private_attrs.get(key, 0) + delta
            # Clamp: non-coin attrs 0-100, coins >= 0
            if key == "coins":
                self.private_attrs[key] = max(0, self.private_attrs[key])
            else:
                self.private_attrs[key] = max(0, min(100, self.private_attrs[key]))
