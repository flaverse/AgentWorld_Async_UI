from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class VisualLayer(Layer):
    visible_radius: int = 5
    sprite: str | None = None

    def __post_init__(self):
        self.observable_radius = self.visible_radius
