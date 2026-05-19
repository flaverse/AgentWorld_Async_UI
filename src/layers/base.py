from dataclasses import dataclass, field


@dataclass
class Layer:
    properties: dict = field(default_factory=dict)
    observable_radius: int = 5

    def observe(self, distance: int) -> dict:
        return {"_distance": distance, **self.properties}
