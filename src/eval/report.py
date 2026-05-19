"""Structured evaluation report. Tables, JSON, summary."""

import json
from dataclasses import dataclass, field


@dataclass
class EvalReport:
    trace_path: str
    n_traces: int
    n_actions: int
    n_agents: int
    agents: list[str]
    results: dict[str, dict] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trace_path": self.trace_path,
            "n_traces": self.n_traces,
            "n_actions": self.n_actions,
            "n_agents": self.n_agents,
            "agents": self.agents,
            "results": self.results,
            "errors": self.errors,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.to_json())

    def to_table(self) -> str:
        lines = []
        lines.append("═" * 66)
        lines.append(f"  AgentWorld Async — Evaluation Report")
        lines.append(f"  Trace: {self.trace_path}")
        lines.append(f"  Actions: {self.n_actions} | Agents: {self.n_agents} | Traces: {self.n_traces}")
        lines.append("═" * 66)

        # Group by category
        categories: dict[str, list[tuple[str, dict]]] = {}
        for name, r in self.results.items():
            cat = r.get("category", "general")
            categories.setdefault(cat, []).append((name, r))

        cat_order = ["social", "behavior", "drive", "narrative", "world", "validation", "general"]
        for cat in cat_order:
            entries = categories.pop(cat, None)
            if not entries:
                continue
            lines.append(f"\n── {cat} ──")
            for name, r in entries:
                val = r.get("value", {})
                src = r.get("source", "")
                src_tag = f"  [{src}]" if src else ""
                lines.append(f"  {name}:{src_tag}")
                lines.append(_fmt_value(val, indent="    "))

        # Any remaining categories
        for cat, entries in sorted(categories.items()):
            lines.append(f"\n── {cat} ──")
            for name, r in entries:
                val = r.get("value", {})
                lines.append(f"  {name}:")
                lines.append(_fmt_value(val, indent="    "))

        # Errors
        if self.errors:
            lines.append(f"\n── errors ({len(self.errors)}) ──")
            for name, msg in self.errors.items():
                lines.append(f"  {name}: {msg}")

        lines.append("═" * 66)
        return "\n".join(lines)

    def summary(self) -> str:
        """One-line high-level summary."""
        parts = [f"{self.n_actions} actions, {self.n_agents} agents"]
        for name, r in self.results.items():
            val = r.get("value", {})
            if isinstance(val, dict) and "summary" in val:
                parts.append(f"{name}={val['summary']}")
        return " | ".join(parts)


def _fmt_value(val, indent: str = "  ") -> str:
    if isinstance(val, dict):
        lines = []
        for k, v in val.items():
            if isinstance(v, list):
                v_str = ", ".join(str(x) for x in v[:5])
                if len(v) > 5:
                    v_str += f" ...(+{len(v)-5})"
                lines.append(f"{indent}{k}: {v_str}")
            elif isinstance(v, dict):
                # Nested dict — flatten to one line
                flat = ", ".join(f"{kk}={vv}" for kk, vv in list(v.items())[:6])
                if len(v) > 6:
                    flat += f" ...(+{len(v)-6})"
                lines.append(f"{indent}{k}: {{{flat}}}")
            elif isinstance(v, float):
                lines.append(f"{indent}{k}: {v:.1f}")
            else:
                lines.append(f"{indent}{k}: {v}")
        return "\n".join(lines)
    elif isinstance(val, list):
        return f"{indent}{val}"
    else:
        return f"{indent}{val}"
