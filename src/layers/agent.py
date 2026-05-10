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
    drives: object = None
    sensory: object = None
    memory: object = None
    knowledge: object = None
    inbox: object = None
