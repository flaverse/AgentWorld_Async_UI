from dataclasses import dataclass, field
from layers.base import Layer


@dataclass
class AgentLayer(Layer):
    autonomous: bool = False
    speed: float = 1.0
    view_radius: int = 20
    hearing_radius: int = 15
    interaction_radius: int = 3
    personality: str = ""
    drive_rates: dict = field(default_factory=dict)
    main_thread: str = ""

    # Runtime modules
    drives: object = None
    sensory: object = None
    memory: object = None

    # ── KL snapshot (P-distribution) ──
    p_channels: dict = field(default_factory=dict)
    p_state:    dict = field(default_factory=dict)
    p_stale:    float = 0.0

    # ── Write-pending lock ──
    _write_pending: bool = False
