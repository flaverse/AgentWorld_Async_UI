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
class HearingRecord:
    entity_id: str = ""
    name: str = ""
    pos: list = field(default_factory=lambda: [0, 0])
    distance: int = 0
    auditory_data: dict = field(default_factory=dict)
    first_heard: float = 0.0
    last_heard: float = 0.0


@dataclass
class SensoryMemory:
    vision: dict[str, VisionRecord] = field(default_factory=dict)
    hearing: dict[str, HearingRecord] = field(default_factory=dict)

    def get_interactable(self) -> list[VisionRecord]:
        return [r for r in self.vision.values() if r.can_interact]

    def get_visible_only(self) -> list[VisionRecord]:
        return [r for r in self.vision.values() if not r.can_interact]

    def clear(self):
        self.vision.clear()
        self.hearing.clear()

    def to_prompt_hearing(self, labels: dict = None) -> str:
        if not labels:
            labels = _default_labels()
        if not self.hearing:
            return ""
        lines = [labels["hearing_header"]]
        for r in self.hearing.values():
            ad = r.auditory_data
            sound = ad.get("sound", "")
            vol = ad.get("volume", "")
            if sound:
                lines.append(labels["hearing_entry"].format(name=r.name, sound=sound, vol=vol))
            else:
                lines.append(labels["hearing_entry"].format(name=r.name, sound=ad.get("sound", ""), vol=vol))
        return "\n".join(lines)

    def to_prompt_vision(self, labels: dict = None) -> str:
        if not labels:
            labels = _default_labels()
        lines = []
        interactable = self.get_interactable()
        if interactable:
            lines.append(labels["interactable_header"])
            for r in interactable:
                extra = f"\n      {labels['expression_label']}: {r.visual_data['detail']}" if "detail" in r.visual_data else ""
                expr = ""
                if "expression" in r.visual_data:
                    expr = f" | {labels['expression_label']} {r.visual_data['expression']}"
                lines.append(
                    f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | {r.visual_data.get('look','')}{expr}"
                    f"\n      {labels['actions_label']}{r.actions}{extra}"
                )
        visible = self.get_visible_only()
        if visible:
            lines.append(f"\n{labels['visible_only_header']}")
            for r in visible:
                expr = ""
                if "expression" in r.visual_data:
                    expr = f" | {labels['expression_label']} {r.visual_data['expression']}"
                lines.append(
                    f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | {labels.get('distance_prefix','距离')}{r.distance} | {r.visual_data.get('look','')}{expr}"
                )
        return "\n".join(lines) if lines else labels["empty_sensory"]


_DEFAULTS = None

def _default_labels():
    global _DEFAULTS
    if _DEFAULTS is None:
        _DEFAULTS = {
            "hearing_header": "## 听觉",
            "hearing_entry": '{name}说: "{sound}" ({vol})',
            "interactable_header": "可交互 (直接选下方ID):",
            "expression_label": "表情:",
            "actions_label": "可做: ",
            "visible_only_header": "看得见够不着:",
            "empty_sensory": "(无)",
            "distance_prefix": "距离",
        }
    return _DEFAULTS
