import time
from dataclasses import dataclass, field


@dataclass
class VisionRecord:
    entity_id: str = ""
    name: str = ""
    pos: list = field(default_factory=lambda: [0, 0])
    distance: int = 0
    visual_data: dict = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    can_interact: bool = False
    first_seen: float = 0.0
    last_seen: float = 0.0


@dataclass
class SensoryMemory:
    vision: dict[str, VisionRecord] = field(default_factory=dict)
    hearing: dict = field(default_factory=dict)

    def get_interactable(self) -> list[VisionRecord]:
        return [r for r in self.vision.values() if r.can_interact]

    def get_visible_only(self) -> list[VisionRecord]:
        return [r for r in self.vision.values() if not r.can_interact]

    def clear(self):
        self.vision.clear()
        self.hearing.clear()

    def to_prompt_vision(self) -> str:
        lines = []
        interactable = self.get_interactable()
        if interactable:
            lines.append("可交互 (直接选下方ID):")
            for r in interactable:
                extra = f"\n      详情: {r.visual_data['detail']}" if "detail" in r.visual_data else ""
                lines.append(
                    f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | {r.visual_data.get('look','')}"
                    f"\n      可做: {r.actions}{extra}"
                )
        visible = self.get_visible_only()
        if visible:
            lines.append("\n看得见够不着:")
            for r in visible:
                lines.append(
                    f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | 距离{r.distance} | {r.visual_data.get('look','')}"
                )
        return "\n".join(lines) if lines else "(无)"
