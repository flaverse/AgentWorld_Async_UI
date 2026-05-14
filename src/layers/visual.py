from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class VisualLayer(Layer):
    visible_radius: int = 5
    sprite: str | None = None
    sprite_sheet: dict | None = None
    properties: dict = field(default_factory=dict)

    def see(self, distance: int) -> dict:
        result = {"look": self.properties.get("look", "")}
        if distance <= 2 and "detail" in self.properties:
            result["detail"] = self.properties["detail"]
        return result
