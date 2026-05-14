from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class InteractionLayer(Layer):
    interaction_radius: int = 2
    public_attrs: dict = field(default_factory=dict)
    private_attrs: dict = field(default_factory=dict)
    actions: dict[str, dict] = field(default_factory=dict)

    def interact(self, action: str | None = None) -> list[str]:
        if action is None:
            return list(self.actions.keys())
        raise NotImplementedError("execute via InteractionSystem")

    def get_action(self, action: str) -> dict | None:
        return self.actions.get(action)

    def apply_deltas(self, deltas: dict) -> None:
        for key, delta in deltas.items():
            try:
                delta = float(delta)
            except (TypeError, ValueError):
                continue
            current = self.private_attrs.get(key, 0)
            try:
                current = float(current)
            except (TypeError, ValueError):
                continue
            self.private_attrs[key] = current + delta
            # Clamp: non-coin attrs 0-100, coins >= 0
            if key == "coins":
                self.private_attrs[key] = max(0, self.private_attrs[key])
            else:
                self.private_attrs[key] = max(0, min(100, self.private_attrs[key]))
