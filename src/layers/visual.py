from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class VisualLayer(Layer):
    visible_radius: int = 5
    sprite: str | None = None
    sprite_sheet: dict | None = None
    info: dict = field(default_factory=dict)

    def see(self, distance: int) -> dict:
        result = {"look": self.info.get("look", "")}
        if distance <= 2 and "detail" in self.info:
            result["detail"] = self.info["detail"]
        return result
