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
    main_thread: str = ""
    template: str = ""   # override agent_decision template per-agent (YAML configurable)
    llm_provider: str = ""  # provider key for multi-LLM routing (YAML configurable)

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

    # ── Conversation state (factual — LLM decides what to do with it) ──
    _last_target_name: str = ""
    _last_expects_reply: bool = False
    _pending_narrative: str = ""   # NPC→Item narrative queues here, LLM #1 decides
