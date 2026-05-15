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

    # Runtime modules
    drives: object = None
    sensory: object = None
    memory: object = None
    knowledge: object = None
    inbox: object = None

    # ── KL snapshot (P-distribution) ──
    p_channels: dict = field(default_factory=dict)
    p_state:    dict = field(default_factory=dict)
    p_stale:    float = 0.0

    # ── Write-pending lock ──
    _write_pending: bool = False

    # ── Duplication check ──
    _last_dialogue: str = ""
    _last_visual:   str = ""
    _last_internal: str = ""

    # ── Observing state (expecting reply from target) ──
    expects_reply:     bool = False
    observing_target:  str = ""
    observing_since:   float = 0.0
    observing_timeout: float = 0.0
