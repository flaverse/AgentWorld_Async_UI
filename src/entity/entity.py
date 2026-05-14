from dataclasses import dataclass, field


@dataclass
class Entity:
    id: str = ""
    name: str = ""
    zone: str = ""
    pos: list[int] = field(default_factory=lambda: [0, 0])
    status: str = "observing"
    last_action_time: float = 0.0

    layers: dict = field(default_factory=dict)
    describe: str = ""
    p_distribution: dict = field(default_factory=dict)

    # Layered KL snapshots — one dict per channel, keyed by entity_id
    p_channels: dict = field(default_factory=dict)
    p_state:    dict = field(default_factory=dict)
    p_stale:    float = 0.0

    # Write-pending lock: skip next decide after interacting
    _write_pending: bool = False

    # observing state
    expects_reply:     bool = False
    observing_target:  str = ""
    observing_since:   float = 0.0
    observing_timeout: float = 0.0

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
