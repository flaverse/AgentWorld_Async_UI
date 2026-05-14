"""Property validation registry. Each validator returns None (pass) or error string (fail)."""
_validators = {}


def register(name: str):
    def decorator(fn):
        _validators[name] = fn
        return fn
    return decorator


def verify(entity, deltas: dict, currency_key: str, drive_min: float, drive_max: float) -> list[str]:
    """Run all registered validators. Returns list of error messages (empty = all pass)."""
    issues = []
    for name, fn in _validators.items():
        msg = fn(entity, deltas, currency_key, drive_min, drive_max)
        if msg:
            issues.append(f"[{name}] {msg}")
    return issues


@register("attribute_bounds")
def check_bounds(entity, deltas: dict, currency_key: str, drive_min: float, drive_max: float) -> str | None:
    inter = entity.get("interaction")
    if not inter: return None
    for attr, delta in deltas.items():
        try: delta = float(delta)
        except (ValueError, TypeError): continue
        current = float(inter.private_attrs.get(attr, 0))
        new_val = current + delta
        if attr == currency_key:
            if new_val < 0:
                return f"{attr} would go negative: {current} + {delta} = {new_val}"
        else:
            if new_val < drive_min:
                return f"{attr} would go below min: {current} + {delta} = {new_val}"
            if new_val > drive_max:
                return f"{attr} would go above max: {current} + {delta} = {new_val}"
    return None


@register("entity_existence")
def check_existence(entity, deltas: dict, *_) -> str | None:
    return None  # entity always exists in current architecture
