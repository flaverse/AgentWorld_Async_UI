"""SensorySystem: 读 target 的 Visual/Auditory Layer → 写 observer.sensory_memory.

原则 ② 分层架构: 每层统一接口 see()/hear()。
原则 ⑤ Systems 总控: 跨层感知逻辑唯一在此。
"""
import time
from agent.sensory_memory import VisionRecord, HearingRecord


class SensorySystem:
    def update(self, observer, all_entities: dict) -> None:
        if not observer.has("agent"):
            return

        agent_layer = observer.get("agent")
        sensory = agent_layer.sensory
        current_vision_ids = set()
        current_hearing_ids = set()

        for entity in all_entities.values():
            if entity.id == observer.id:
                continue
            if entity.zone != observer.zone:
                continue

            d = observer.distance_to(entity)

            # ── 视觉 (VisualLayer.see) ──
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
                        entity_id=entity.id, name=entity.name,
                        pos=list(entity.pos), distance=d,
                        visual_data=vision_data, actions=actions,
                        can_interact=False,
                        first_seen=(time.time() if is_new
                                    else sensory.vision[entity.id].first_seen),
                        last_seen=time.time(),
                    )

            # ── 听觉 (AuditoryLayer.hear) ──
            if entity.has("auditory"):
                auditory_layer = entity.get("auditory")
                hear_range = min(agent_layer.hearing_radius,
                                 auditory_layer.audible_radius)
                if d <= hear_range:
                    current_hearing_ids.add(entity.id)
                    is_new = entity.id not in sensory.hearing
                    auditory_data = auditory_layer.hear(d)
                    sensory.hearing[entity.id] = HearingRecord(
                        entity_id=entity.id, name=entity.name,
                        pos=list(entity.pos), distance=d,
                        auditory_data=auditory_data,
                        first_heard=(time.time() if is_new
                                     else sensory.hearing[entity.id].first_heard),
                        last_heard=time.time(),
                    )

        # 离开范围 → 删除
        for eid in list(sensory.vision.keys()):
            if eid not in current_vision_ids:
                del sensory.vision[eid]
        for eid in list(sensory.hearing.keys()):
            if eid not in current_hearing_ids:
                del sensory.hearing[eid]
