"""Terminal summary report with optional validation checks."""
from .runner import TraceCollector


def report(collector: TraceCollector, agents: list, sim: dict,
           elapsed: float, validate: bool, output_path: str):
    """Print summary and optional validation report."""
    merged = collector.merged()
    if output_path:
        collector.save(output_path)

    actions = [t for t in merged if t.get("action_text")]
    results = [t for t in merged if t.get("result_narrative")]

    print(f"  Complete: {len(merged)} traces, {len(actions)} actions, "
          f"{len(results)} results, {elapsed:.0f}s")
    for name in sorted(set(t.get("agent", "") for t in merged)):
        agent_acts = [t for t in actions if t["agent"] == name]
        print(f"    {name:6s}: {len(agent_acts)} acts")
    if output_path:
        print(f"  Data: {output_path}")

    if not validate:
        return

    npc_names = {a.name for a in agents}
    npc_acts = sum(1 for t in actions
                   if t.get("target") in npc_names
                   and t.get("agent", "") in npc_names
                   and t["agent"] != t["target"])

    v = sim.get("validation", {})
    delta_max = v.get("delta_max", 30)
    drive_min = v.get("drive_min", 0)
    drive_max = v.get("drive_max", 100)
    currency = sim.get("currency", "coins")
    issues = []
    for t in actions:
        deltas = t.get('result_caller_deltas')
        if not isinstance(deltas, dict):
            continue
        for attr, val in deltas.items():
            if isinstance(val, (int, float)) and attr != currency and abs(val) > delta_max:
                issues.append(f"large delta: {t['agent']} {attr}={val}")
    for t in merged:
        drives = t.get('drives', {})
        for attr, val in drives.items():
            if attr == currency:
                continue
            if isinstance(val, (int, float)) and (val < drive_min or val > drive_max):
                issues.append(f"drive out of range: {t['agent']} {attr}={val}")
    if issues:
        print(f"\n  ⚠️  {len(issues)} issues:")
        for i in issues[:10]:
            print(f"    - {i}")
    else:
        print(f"  ✅ All validation checks passed.")
    print(f"  total_actions={len(actions)} npc_npc={npc_acts}")
