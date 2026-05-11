"""EventBus — 异步发布/订阅。消除代码中所有轮询模式。

原则 ⑤ Systems 总控: EventBus 是 World 拥有的基础设施。
System 订阅事件, Entity/Layer 不知 EventBus 存在。

可用事件:
  entity.spawned(entity_id, zone, pos)
  entity.despawned(entity_id, zone, pos)  
  entity.moved(entity_id, old_pos, new_pos, zone)
  entity.zone_changed(entity_id, old_zone, new_zone, old_pos, new_pos)
  interaction.completed(agent_id, result)
  world.tick(time_str)
"""
import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list] = defaultdict(list)

    def on(self, event: str, callback):
        """Subscribe to event. callback(event_name, **kwargs)."""
        self._subscribers[event].append(callback)

    async def emit(self, event: str, **kwargs):
        """Emit event to all subscribers. Non-blocking (gather)."""
        callbacks = self._subscribers.get(event, [])
        if not callbacks:
            return
        tasks = [cb(event, **kwargs) for cb in callbacks]
        await asyncio.gather(*tasks, return_exceptions=True)

    def emit_sync(self, event: str, **kwargs):
        """Synchronous emit for callbacks that don't await anything.
        Used from non-async contexts (e.g., Entity.move_to)."""
        for cb in self._subscribers.get(event, []):
            try:
                cb(event, **kwargs)
            except Exception:
                pass
