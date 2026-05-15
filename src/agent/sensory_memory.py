from dataclasses import dataclass, field


@dataclass
class SensorRecord:
    entity_id: str = ""
    name: str = ""
    pos: list = field(default_factory=lambda: [0, 0])
    distance: int = 0
    data: dict = field(default_factory=dict)
    first_seen: float = 0.0
    last_seen: float = 0.0


@dataclass
class SensoryMemory:
    channels: dict[str, dict[str, SensorRecord]] = field(
        default_factory=lambda: {"visual": {}, "auditory": {}})

    def clear(self):
        for ch in self.channels.values():
            ch.clear()

    def to_prompt(self, layer_name: str, labels: dict = None) -> str:
        if labels is None:
            labels = _default_labels()
        ch = self.channels.get(layer_name, {})
        if not ch:
            return ""
        lines = []
        for r in ch.values():
            # Generic rendering: dump all data keys
            for key, val in r.data.items():
                if key.startswith("_"):
                    continue
                if isinstance(val, str) and val:
                    lines.append(f"  [{layer_name}] {r.name}: {val}")
        return "\n".join(lines) if lines else ""


_DEFAULTS = None

def _default_labels():
    global _DEFAULTS
    if _DEFAULTS is None:
        _DEFAULTS = {"empty": "(无)"}
    return _DEFAULTS
