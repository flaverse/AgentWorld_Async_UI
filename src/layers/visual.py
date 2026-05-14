from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class VisualLayer(Layer):
    visible_radius: int = 5
    sprite: str | None = None
    sprite_sheet: dict | None = None
    properties: dict = field(default_factory=dict)

    def see(self, distance: int) -> dict:
        return {"_distance": distance, **self.properties.copy()}
