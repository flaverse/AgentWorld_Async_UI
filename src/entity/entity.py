from dataclasses import dataclass, field


@dataclass
class Entity:
    id: str = ""
    name: str = ""
    zone: str = ""
    pos: list[int] = field(default_factory=lambda: [0, 0])
    status: str = "idle"
    busy_until: float = 0.0
    busy_result: object = None
    last_action_time: float = 0.0

    layers: dict = field(default_factory=dict)

    def has(self, layer_name: str) -> bool:
        return layer_name in self.layers

    def get(self, layer_name: str):
        return self.layers.get(layer_name)

    def distance_to(self, other: 'Entity') -> int:
        return abs(self.pos[0] - other.pos[0]) + abs(self.pos[1] - other.pos[1])

    def move_to(self, target_pos: list[int]) -> int:
        dist = abs(self.pos[0] - target_pos[0]) + abs(self.pos[1] - target_pos[1])
        self.pos = target_pos
        agent_layer = self.get("agent")
        speed = agent_layer.speed if agent_layer else 1.0
        return int(dist * speed)

    def apply_deltas(self, deltas: dict) -> None:
        interaction = self.get("interaction")
        if interaction:
            interaction.apply_deltas(deltas)

    def calc_facing(self, to_pos: list[int]) -> str:
        dx = to_pos[0] - self.pos[0]
        dy = to_pos[1] - self.pos[1]
        if abs(dx) >= abs(dy):
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"
