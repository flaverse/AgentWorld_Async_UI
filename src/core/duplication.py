"""Output-level duplication check. @register chain, YAML-configurable mask.
v1-style: each channel independently validates, mask controls activation.
"""
_registry = {}


def register(name: str):
    def decorator(fn):
        _registry[name] = fn
        return fn
    return decorator


def check(agent, decision, mask: list[str], prefix_len: int) -> dict[str, bool]:
    """按 mask 跑注册链。返回 {channel_name: True=allowed, False=mute}。"""
    result = {}
    for channel in mask:
        if channel in _registry:
            ok = _registry[channel](agent, decision, prefix_len)
            result[channel] = ok
    return result


@register("dialogue")
def _dialogue_dup(agent, decision, n):
    d = decision.get("dialogue", "")
    return not (d and d[:n] == getattr(agent, '_last_dialogue', '')[:n])


@register("visual")
def _visual_dup(agent, decision, n):
    v = decision.get("visual", "")
    return not (v and v[:n] == getattr(agent, '_last_visual', '')[:n])


@register("internal")
def _internal_dup(agent, decision, n):
    i = decision.get("internal", "")
    return not (i and i[:n] == getattr(agent, '_last_internal', '')[:n])
