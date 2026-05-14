from dataclasses import dataclass, field


_DEFAULT_LABELS = {
    "drive_table_header": "| 属性 | 数值 |",
    "drive_table_sep":    "|------|------|",
    "drive_urgent":       "⚠️急需",
    "drive_needed":       "●需要",
    "drive_normal":       "○正常",
    "drive_no_data":      "(无数据)",
}


@dataclass
class DriveSystem:
    attrs: dict = field(default_factory=dict)
    decay_rates: dict[str, float] = field(default_factory=dict)
    currency_key: str = "coins"
    drive_min: float = 0.0
    drive_max: float = 100.0
    urgent_threshold: float = 80.0
    needed_threshold: float = 60.0

    def decay(self, elapsed_minutes: float) -> None:
        for key, rate in self.decay_rates.items():
            if key in self.attrs:
                val = self.attrs.get(key, 0.0) + rate * elapsed_minutes
                self.attrs[key] = max(self.drive_min, min(self.drive_max, val))

    def to_prompt_table(self, labels: dict = None) -> str:
        if labels is None:
            labels = _DEFAULT_LABELS
        lines = [labels["drive_table_header"], labels["drive_table_sep"]]
        for key, val in self.attrs.items():
            if key == self.currency_key:
                continue
            if val >= self.urgent_threshold:
                urgency = labels["drive_urgent"]
            elif val >= self.needed_threshold:
                urgency = labels["drive_needed"]
            else:
                urgency = labels["drive_normal"]
            lines.append(f"| {key} | {val:.0f}/{self.drive_max:.0f} {urgency} |")
        return "\n".join(lines) if len(lines) > 2 else labels["drive_no_data"]
