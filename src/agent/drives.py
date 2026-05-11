from dataclasses import dataclass, field


@dataclass
class DriveSystem:
    """Agent 欲望系统。直接引用 InteractionLayer.private_attrs，不持有副本。
    
    原则 ⑩ 属性平权: coins / thirst / hunger 无区别。
    原则 ② 分层架构: DriveSystem 是 AgentLayer 的"计算器"，数据源在 InteractionLayer。
    """
    attrs: dict = field(default_factory=dict)          # → 引用 private_attrs
    decay_rates: dict[str, float] = field(default_factory=dict)

    def decay(self, elapsed_minutes: float) -> None:
        for key, rate in self.decay_rates.items():
            if key in self.attrs:
                self.attrs[key] = self.attrs.get(key, 0.0) + rate * elapsed_minutes
                self.attrs[key] = max(0.0, min(100.0, self.attrs[key]))

    def to_prompt_table(self) -> str:
        lines = ["| 属性 | 数值 |", "|------|------|"]
        for key, val in self.attrs.items():
            if key == "coins":
                continue  # coins shown separately
            if val >= 80:
                urgency = "⚠️急需"
            elif val >= 60:
                urgency = "●需要"
            else:
                urgency = "○正常"
            lines.append(f"| {key} | {val:.0f}/100 {urgency} |")
        return "\n".join(lines) if len(lines) > 2 else "(无数据)"
