"""Output-level duplication check. @register chain, YAML-configurable mask.
Validators are channel-agnostic. Mask declares which validator each channel opts into.
Only blocks consecutive repeats. Reference updates on each non-muted output.
"""
_registry = {}


def register(name: str):
    def decorator(fn):
        _registry[name] = fn
        return fn
    return decorator


def check(agent_layer, decision, mask: dict[str, list], prefix_len: int) -> dict[str, bool]:
    """按 mask 跑注册链。返回 {channel_name: True=allowed, False=mute}。
    通过时更新 _last_{channel} 参考值；被 mute 时保留旧参考值。
    """
    result = {}
    for channel, validators in mask.items():
        allowed = True
        for vname in validators:
            if vname in _registry and not _registry[vname](agent_layer, decision, channel, prefix_len):
                allowed = False
                break
        if allowed:
            setattr(agent_layer, f'_last_{channel}', decision.get(channel, ""))
        result[channel] = allowed
    return result


@register("mute")
def _mute(agent_layer, decision, channel, n):
    """防重复: 当前输出[:n] == 上次通过输出[:n] → 拒绝。"""
    d = decision.get(channel, "")
    last = getattr(agent_layer, f'_last_{channel}', '')
    return not (d and last and d[:n] == last[:n])
