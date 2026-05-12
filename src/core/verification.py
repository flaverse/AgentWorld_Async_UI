"""Verification layer — check registry with mask-based activation.

Inspired by v1 verification_registry.py.
每个校验项通过 @register 装饰器注册。掩码激活指定校验子集。
失败时生成结构化反馈文本，回注 LLM #3 重试。
"""
from dataclasses import dataclass, field


@dataclass
class CheckFailure:
    code: str
    message: str
    fix_hint: str = ""
    details: dict = field(default_factory=dict)


class CheckPassed:
    pass


_registry: dict[str, dict] = {}


def register(code: str, name: str, desc: str):
    """注册一个校验项。返回装饰器。"""
    def decorator(fn):
        _registry[code] = {
            "name": name,
            "desc": desc,
            "fn": fn,
        }
        return fn
    return decorator


# ═══════════════════════════════════════
# Built-in checks
# ═══════════════════════════════════════

@register("attribute_bounds", "属性边界", "任意属性不能越 [0,100]，coins 不能负")
def check_attribute_bounds(effects: list, entities: dict) -> CheckPassed | CheckFailure:
    for eff in effects:
        eid = eff.get("entity_id", "")
        if eid not in entities:
            continue
        entity = entities[eid]
        interaction = entity.get("interaction") if hasattr(entity, 'get') else None
        if not interaction:
            continue
        for attr, delta in eff.get("deltas", {}).items():
            current = interaction.private_attrs.get(attr, 0)
            try:
                current = float(current)
                delta = float(delta)
            except (TypeError, ValueError):
                continue
            new_val = current + delta
            if attr == "coins" and new_val < 0:
                return CheckFailure(
                    code="attribute_bounds",
                    message=f"{entity.name}.{attr} 会变成 {new_val:.0f} (负值)",
                    fix_hint=f"减少 {attr} 的消耗量或标记为不可执行",
                    details={"entity": entity.name, "attr": attr, "current": current, "delta": delta},
                )
            if attr != "coins" and (new_val < 0 or new_val > 100):
                return CheckFailure(
                    code="attribute_bounds",
                    message=f"{entity.name}.{attr} 会变成 {new_val:.0f} (越界 [0,100])",
                    fix_hint=f"调整 {attr} 的 delta 值到合理范围",
                    details={"entity": entity.name, "attr": attr, "current": current, "delta": delta},
                )
    return CheckPassed()


@register("entity_existence", "实体存在", "effects 中引用的 entity_id 必须存在于世界中")
def check_entity_existence(effects: list, entities: dict) -> CheckPassed | CheckFailure:
    for eff in effects:
        eid = eff.get("entity_id", "")
        if eid and eid not in entities:
            return CheckFailure(
                code="entity_existence",
                message=f"effects 引用了不存在的实体: {eid}",
                fix_hint="移除该 entity 的 effects 条目或确保 entity_id 正确",
            )
    return CheckPassed()


@register("conservation", "度守恒", "coins 等守恒属性的转移必须在实体间平衡 (Σ=0)")
def check_conservation(effects: list, entities: dict) -> CheckPassed | CheckFailure:
    conserved_attrs = {"coins", "stock"}
    for attr in conserved_attrs:
        total = sum(
            float(eff.get("deltas", {}).get(attr, 0))
            for eff in effects
        )
        if abs(total) > 0.01:
            return CheckFailure(
                code="conservation",
                message=f"{attr} 不守恒: 总变化 {total:+.1f} (应为 0)",
                fix_hint=f"确保 {attr} 的增减平衡 (一方减少多少, 另一方增加多少)",
                details={"attr": attr, "total_delta": total},
            )
    return CheckPassed()


# ═══════════════════════════════════════
# Verifier
# ═══════════════════════════════════════

class Verifier:
    def __init__(self, mask: list[str] | None = None):
        self.mask = mask

    def verify(self, effects: list, entities: dict) -> list[CheckFailure]:
        """执行所有激活的校验项。返回失败的列表。"""
        failures = []
        for code, check in _registry.items():
            if self.mask is None or code in self.mask:
                result = check["fn"](effects, entities)
                if isinstance(result, CheckFailure):
                    failures.append(result)
        return failures


def build_feedback(failures: list[CheckFailure], context: str = "") -> str:
    """生成结构化反馈文本，用于回注 LLM prompt。"""
    if not failures:
        return ""
    lines = ["## 上次投影校验失败，请修正:", ""]
    if context:
        lines.append(f"参考上下文: {context}")
        lines.append("")
    for f in failures:
        lines.append(f"- [{f.code}] {f.message}")
        if f.fix_hint:
            lines.append(f"  修正建议: {f.fix_hint}")
        lines.append("")
    lines.append("请重新生成 projections (deltas)，确保通过以上校验。")
    return "\n".join(lines)
