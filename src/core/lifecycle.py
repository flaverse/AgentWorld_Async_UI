"""EntityLifecycle — 统一实体生命周期管理。

原则 ⑤ Systems 总控: 所有 Entity 创建/销毁/zone迁移统一走此入口。
原则 ③ 位置即关系: 迁移只改坐标,不改关系字段。
"""


class EntityLifecycle:
    """Wraps World 的 entities dict + grids + event_bus。
    Entity 的 spawn/despawn/zone_transfer 的唯一入口。
    """

    def __init__(self, world):
        self.world = world
        self.bus = getattr(world, 'event_bus', None)

    def spawn(self, entity) -> None:
        """注册新 Entity。更新 entities dict + spatial grid + emit 事件。"""
        w = self.world
        w.entities[entity.id] = entity
        entity._world = w

        if entity.zone in w.grids:
            w.grids[entity.zone].insert(entity.id, entity.pos)

        if self.bus:
            self.bus.emit_sync("entity.spawned",
                               entity_id=entity.id, zone=entity.zone,
                               pos=list(entity.pos))

    def despawn(self, entity_id: str) -> bool:
        """注销 Entity。从 entities dict + grid 移除 + emit 事件。
        返回 True 如果实体存在并已移除。"""
        w = self.world
        entity = w.entities.pop(entity_id, None)
        if not entity:
            return False

        if entity.zone in w.grids:
            w.grids[entity.zone].remove(entity_id, entity.pos)

        # Also remove from active_events if event entity
        w.active_events.pop(entity_id, None)

        if self.bus:
            self.bus.emit_sync("entity.despawned",
                               entity_id=entity_id, zone=entity.zone,
                               pos=list(entity.pos))
        return True

    def transfer_zone(self, entity, new_zone: str, new_pos: list[int]) -> None:
        """跨 Zone 迁移实体。更新 grid + entity zone+pos + emit 事件 + 清 sensory。"""
        old_zone = entity.zone
        old_pos = list(entity.pos)

        # 从旧 zone 的 grid 移除
        if old_zone in self.world.grids:
            self.world.grids[old_zone].remove(entity.id, old_pos)

        # 更新 entity 自身
        entity.zone = new_zone
        entity.pos = new_pos

        # 加入新 zone 的 grid
        if new_zone in self.world.grids:
            self.world.grids[new_zone].insert(entity.id, new_pos)

        # 清 agent sensory
        if entity.has("agent"):
            ag = entity.get("agent")
            if ag.sensory:
                ag.sensory.clear()

        # 发射事件
        if self.bus:
            self.bus.emit_sync("entity.zone_changed",
                               entity_id=entity.id,
                               old_zone=old_zone, new_zone=new_zone,
                               old_pos=old_pos, new_pos=new_pos)
