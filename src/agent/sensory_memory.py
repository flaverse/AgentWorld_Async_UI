from dataclasses import dataclass, field
from prompt.assembler import safe_format


@dataclass
class SensorRecord:
    entity_id: str = ""
    name: str = ""
    distance: int = 0
    data: dict = field(default_factory=dict)
    first_seen: float = 0.0


@dataclass
class SensoryMemory:
    channels: dict = field(default_factory=dict)

    def clear(self):
        for ch in self.channels.values():
            ch.clear()

    def to_prompt(self, layer_name: str, cfg: dict) -> str:
        """Template-driven channel rendering. cfg from YAML sensory_prompts."""
        ch = self.channels.get(layer_name, {})
        if not ch:
            return ""
        lines = [cfg.get("header", layer_name)]
        slot_keys = [k for k in cfg if k != "header"]
        for r in ch.values():
            ctx = {**r.data, "name": r.name, "distance": r.distance}
            for key in slot_keys:
                tpl = cfg.get(key, "")
                if tpl:
                    line = safe_format(tpl, ctx)
                    if line.strip() and "{" not in line:
                        lines.append(line)
        return "\n".join(lines)
