"""Output-level duplication check. @register chain, YAML-configurable mask.
Only blocks consecutive repeats. Reference updates on each non-muted output.
"""
_registry = {}


def register(name: str):
    def decorator(fn):
        _registry[name] = fn
        return fn
    return decorator


def check(agent, decision, mask: list[str], prefix_len: int) -> dict[str, bool]:
    """按 mask 跑注册链。返回 {channel_name: True=allowed, False=mute}。
    通过时更新 _last_* 参考值；被 mute 时保留旧参考值。
    """
    result = {}
    for channel in mask:
        if channel in _registry:
            ok = _registry[channel](agent, decision, prefix_len)
            if ok:
                # Update reference on success
                ref_attr = f'_last_{channel}'
                setattr(agent, ref_attr, decision.get(channel, ""))
            result[channel] = ok
    return result


@register("dialogue")
def _dialogue_dup(agent, decision, n):
    d = decision.get("dialogue", "")
    last = getattr(agent, '_last_dialogue', '')
    return not (d and last and d[:n] == last[:n])


@register("visual")
def _visual_dup(agent, decision, n):
    v = decision.get("visual", "")
    last = getattr(agent, '_last_visual', '')
    return not (v and last and v[:n] == last[:n])


@register("internal")
def _internal_dup(agent, decision, n):
    i = decision.get("internal", "")
    last = getattr(agent, '_last_internal', '')
    return not (i and last and i[:n] == last[:n])
