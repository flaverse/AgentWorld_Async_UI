import time
from agent.sensory_memory import VisionRecord


class SensorySystem:
    def update(self, observer, all_entities: dict) -> None:
        if not observer.has("agent"):
            return

        agent_layer = observer.get("agent")
        sensory = agent_layer.sensory
        current_vision_ids = set()

        for entity in all_entities.values():
            if entity.id == observer.id:
                continue
            if entity.zone != observer.zone:
                continue

            d = observer.distance_to(entity)

            if entity.has("visual"):
                visual_layer = entity.get("visual")
                see_range = min(agent_layer.view_radius, visual_layer.visible_radius)

                if d <= see_range:
                    current_vision_ids.add(entity.id)
                    is_new = entity.id not in sensory.vision

                    vision_data = visual_layer.see(d)
                    actions = []
                    if entity.has("interaction"):
                        actions = entity.get("interaction").interact()

                    sensory.vision[entity.id] = VisionRecord(
                        entity_id=entity.id,
                        name=entity.name,
                        pos=list(entity.pos),
                        distance=d,
                        visual_data=vision_data,
                        actions=actions,
                        can_interact=False,
                        first_seen=(time.time() if is_new
                                    else sensory.vision[entity.id].first_seen),
                        last_seen=time.time(),
                    )

        for eid in list(sensory.vision.keys()):
            if eid not in current_vision_ids:
                del sensory.vision[eid]
