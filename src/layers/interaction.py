from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class InteractionLayer(Layer):
    interaction_radius: int = 2
    private_attrs: dict = field(default_factory=dict)
    hidden: dict = field(default_factory=dict)
    gate: dict | None = None
    currency_key: str = "coins"
    drive_min: float = 0.0
    drive_max: float = 100.0
    attr_bounds: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.interaction_radius:
            self.observable_radius = self.interaction_radius

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
            if key == self.currency_key:
                self.private_attrs[key] = max(0, self.private_attrs[key])
            else:
                bounds = self.attr_bounds.get(key, {})
                lo = bounds.get("min", self.drive_min)
                hi = bounds.get("max", self.drive_max)
                self.private_attrs[key] = max(lo, min(hi, self.private_attrs[key]))
