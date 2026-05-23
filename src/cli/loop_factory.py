"""LoopConfig construction and per-agent drive injection."""
from loop import LoopConfig


def build_loop_config(sim: dict, labels: dict) -> LoopConfig:
    """Construct LoopConfig from YAML simulation block.
    All params sourced from sim dict with safe defaults.
    """
    kl = sim.get("kl", {})
    return LoopConfig(
        poll_interval=sim.get("poll_interval", 0.3),
        thresholds=kl.get("state_thresholds", [30, 60, 80]),
        coin_epsilon=kl.get("coin_epsilon", 5),
        stale_timeout=sim.get("stale_timeout", 30),
        currency=sim.get("currency", "coins"),
        text=sim.get("text", {}),
        labels=labels,
        default_patience=sim.get("default_patience", 5),
        memory_prompt_count=sim.get("memory_prompt_count", 5),
    )


def setup_agent_drives(agents: list, sim: dict, currency: str) -> None:
    """Inject per-attribute drive config into existing DriveSystem + InteractionLayer."""
    drive_cfg = sim.get("drive", {})
    attr_cfg = drive_cfg.get("attributes", {})
    for e in agents:
        al = e.get("agent")
        inter = e.get("interaction")
        if al and al.drives:
            al.drives.attr_cfg = attr_cfg
        if inter:
            inter.attr_bounds = {k: {"min": v.get("min", 0), "max": v.get("max", 100)}
                                 for k, v in attr_cfg.items()}
            inter.currency_key = currency
