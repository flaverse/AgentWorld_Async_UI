from dataclasses import dataclass
from layers.base import Layer


@dataclass
class AuditoryLayer(Layer):
    audible_radius: int = 10

    def __post_init__(self):
        self.observable_radius = self.audible_radius
