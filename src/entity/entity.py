from dataclasses import dataclass, field


@dataclass
class Entity:
    id: str = ""
    name: str = ""
    zone: str = ""
    pos: list[int] = field(default_factory=lambda: [0, 0])
    last_action_time: float = 0.0

    layers: dict = field(default_factory=dict)
    describe: str = ""

    _world: object = None

    def has(self, layer_name: str) -> bool:
        return layer_name in self.layers

    def get(self, layer_name: str):
        return self.layers.get(layer_name)

    def distance_to(self, other: 'Entity') -> int:
        return abs(self.pos[0] - other.pos[0]) + abs(self.pos[1] - other.pos[1])

    def move_to(self, target_pos: list[int]) -> int:
        dist = abs(self.pos[0] - target_pos[0]) + abs(self.pos[1] - target_pos[1])
        old_pos = list(self.pos)
        self.pos = target_pos
        agent_layer = self.get("agent")
        speed = agent_layer.speed if agent_layer else 1.0
        if self._world:
            self._world.notify_moved(self.id, old_pos, target_pos, self.zone)
        return int(dist * speed)
