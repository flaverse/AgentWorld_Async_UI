"""SensorySystem: 遍历 entity.layers → observe() → 写入 observer.sensory.channels。
所有 layer 统一处理。零硬编码层名。
"""
import time
from agent.sensory_memory import SensorRecord


class SensorySystem:
    def update(self, observer, all_entities: dict, world=None,
               speech_window: int = 30) -> None:
        if not observer.has("agent"):
            return

        agent_layer = observer.get("agent")
        sensory = agent_layer.sensory

        max_radius = max(agent_layer.view_radius, agent_layer.hearing_radius)
        if world:
            candidate_ids = world.get_nearby_ids(observer.zone, observer.pos, max_radius)
        else:
            candidate_ids = [eid for eid, e in all_entities.items()
                             if e.zone == observer.zone and e.id != observer.id]

        # Track which entities are currently visible per channel
        current = {}  # {layer_name: set(entity_id)}

        for eid in candidate_ids:
            entity = all_entities.get(eid)
            if not entity or entity.id == observer.id:
                continue
            d = observer.distance_to(entity)

            for layer_name, layer in entity.layers.items():
                if not hasattr(layer, "observe"):
                    continue
                if d > getattr(layer, "observable_radius", 5):
                    continue

                # Auditory special handling: only poll if speech is recent
                if layer_name == "auditory":
                    speech = layer.properties.get("current_speech", "")
                    speech_ts = layer.properties.get("speech_ts", 0)
                    if not speech or time.time() - speech_ts > speech_window:
                        continue

                if layer_name not in sensory.channels:
                    sensory.channels[layer_name] = {}
                if layer_name not in current:
                    current[layer_name] = set()

                current[layer_name].add(eid)
                is_new = eid not in sensory.channels[layer_name]
                data = layer.observe(d)

                sensory.channels[layer_name][eid] = SensorRecord(
                    entity_id=eid, name=entity.name,
                    pos=list(entity.pos), distance=d,
                    data=data,
                    first_seen=(time.time() if is_new
                                else sensory.channels[layer_name][eid].first_seen),
                    last_seen=time.time(),
                )

                # Hearing → memory retention
                if layer_name == "auditory" and is_new and observer.has("agent"):
                    observer.get("agent").memory.record(
                        f"{entity.name}说：\"{speech}\"")

        # Cleanup: remove entities that left range
        for layer_name, ch in list(sensory.channels.items()):
            current_ids = current.get(layer_name, set())
            for eid in list(ch.keys()):
                if eid not in current_ids:
                    del ch[eid]
