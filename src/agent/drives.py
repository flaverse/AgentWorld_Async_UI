from dataclasses import dataclass, field


@dataclass
class DriveSystem:
    attrs: dict = field(default_factory=dict)
    attr_cfg: dict = field(default_factory=dict)
    drive_min: float = 0.0
    drive_max: float = 100.0

    def decay(self, elapsed_minutes: float) -> None:
        for name, cfg in self.attr_cfg.items():
            rate = cfg.get("decay", 0)
            if rate != 0 and name in self.attrs:
                val = self.attrs.get(name, 0.0) + rate * elapsed_minutes
                lo = cfg.get("min", self.drive_min)
                hi = cfg.get("max", self.drive_max)
                self.attrs[name] = max(lo, min(hi, val))

    def to_prompt(self) -> str:
        if not self.attrs:
            return ""
        lines = ["| 属性 | 数值 | 描述 |", "|------|------|------|"]
        for name, cfg in self.attr_cfg.items():
            val = self.attrs.get(name)
            if val is None: continue
            hi = cfg.get("max", self.drive_max)
            desc = cfg.get("description", "")
            lines.append(f"| {name} | {val:.0f}/{hi:.0f} | {desc} |")
        return "\n".join(lines)
