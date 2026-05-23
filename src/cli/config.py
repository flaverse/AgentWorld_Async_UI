"""Configuration loading: YAML, LLM clients, prompt assembler."""
import os
import yaml

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override keys take precedence."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(world_path: str | None = None):
    """Load world, prompt, and LLM configs. Returns structured dict.
    World YAML inherits simulation defaults from _sim_defaults.yaml.
    """
    with open(os.path.join(base_dir, "config/_sim_defaults.yaml")) as f:
        defaults = yaml.safe_load(f)
    w_path = world_path or os.path.join(base_dir, "config/world.yaml")
    with open(w_path) as f:
        wc = yaml.safe_load(f)
    if "world" in wc and "simulation" not in wc["world"]:
        wc["world"]["simulation"] = defaults["simulation"]
    else:
        wc["world"]["simulation"] = _deep_merge(
            defaults["simulation"],
            wc.get("world", {}).get("simulation", {}))
    with open(os.path.join(base_dir, "config/llm.yaml")) as f:
        lc = yaml.safe_load(f)

    from llm.concurrency import ConcurrencyGate
    from telemetry.collector import TelemetryCollector
    from llm.client import LLMClient
    telemetry = TelemetryCollector()
    providers_cfg = lc.get("providers", {"deepseek": lc})
    llm_clients: dict[str, object] = {}
    concurrency_gates: dict[str, object] = {}
    default_provider = lc.get("default_provider", list(providers_cfg.keys())[0])
    for pname, pcfg in providers_cfg.items():
        pcfg["provider"] = pname
        cc_cfg = pcfg.pop("concurrency", {})
        gate = ConcurrencyGate(
            initial=cc_cfg.get("initial", 8),
            success_window=cc_cfg.get("success_window_sec", 30),
        )
        llm_clients[pname] = LLMClient(pcfg, concurrency_gate=gate, telemetry=telemetry)
        concurrency_gates[pname] = gate

    from prompt.loader import PromptLoader
    from prompt.assembler import PromptAssembler
    loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    labels = loader.data.get("text_labels", {})
    labels["sensory_prompts"] = loader.data.get("sensory_prompts", {})
    return {"world": wc, "llm_clients": llm_clients, "llm_config": lc,
            "assembler": assembler, "labels": labels,
            "default_provider": default_provider,
            "concurrency_gates": concurrency_gates,
            "telemetry": telemetry}
