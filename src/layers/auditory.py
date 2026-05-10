from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class AuditoryLayer(Layer):
    audible_radius: int = 10
    info: dict = field(default_factory=dict)

    def hear(self, distance: int) -> dict:
        vol = "响亮" if distance <= 3 else "中等" if distance <= 8 else "隐约"
        return {
            "sound": self.info.get("sound", ""),
            "volume": vol,
        }
