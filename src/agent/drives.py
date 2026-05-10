from dataclasses import dataclass, field


@dataclass
class DriveSystem:
    values: dict[str, float] = field(default_factory=dict)
    decay_rates: dict[str, float] = field(default_factory=dict)

    def decay(self, elapsed_minutes: float) -> None:
        for key, rate in self.decay_rates.items():
            if key in self.values:
                self.values[key] += rate * elapsed_minutes
                self.values[key] = max(0.0, min(100.0, self.values[key]))

    def apply_deltas(self, deltas: dict) -> None:
        for key, delta in deltas.items():
            self.values[key] = self.values.get(key, 0.0) + delta

    def to_prompt_table(self) -> str:
        lines = ["| 属性 | 数值 |", "|------|------|"]
        for key, val in self.values.items():
            if val >= 80:
                urgency = "⚠️急需"
            elif val >= 60:
                urgency = "●需要"
            else:
                urgency = "○正常"
            lines.append(f"| {key} | {val:.0f}/100 {urgency} |")
        return "\n".join(lines)
