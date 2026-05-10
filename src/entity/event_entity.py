import time
from dataclasses import dataclass, field
from entity.entity import Entity


@dataclass
class EventEntity(Entity):
    spawned_at: float = 0.0
    lifespan_minutes: float = 3.0
    source_entity_id: str = ""
    source_action: str = ""

    def is_expired(self, now: float) -> bool:
        return (now - self.spawned_at) >= self.lifespan_minutes
