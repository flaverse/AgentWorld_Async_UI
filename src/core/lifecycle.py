"""EntityLifecycle — 统一实体生命周期管理。"""


class EntityLifecycle:

    def __init__(self, world):
        self.world = world

    def spawn(self, entity) -> None:
        w = self.world
        w.entities[entity.id] = entity
        entity._world = w
        if entity.zone in w.grids:
            w.grids[entity.zone].insert(entity.id, entity.pos)

    def transfer_zone(self, entity, new_zone: str, new_pos: list[int]) -> None:
        old_zone = entity.zone
        old_pos = list(entity.pos)

        if old_zone in self.world.grids:
            self.world.grids[old_zone].remove(entity.id, old_pos)

        entity.zone = new_zone
        entity.pos = new_pos

        if new_zone in self.world.grids:
            self.world.grids[new_zone].insert(entity.id, new_pos)

        if entity.has("agent"):
            ag = entity.get("agent")
            if ag.sensory:
                ag.sensory.clear()
