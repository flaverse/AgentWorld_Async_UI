"""World and agent construction. Pure config→instance mapping."""
from core.world import World
from agent.brain import Brain
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem


def spawn_world(cfg: dict):
    """Create World, Brain, and Systems from loaded config.
    Returns (world, brain, systems_dict).
    """
    clients = cfg["llm_clients"]
    default_llm = clients.get(cfg["default_provider"], list(clients.values())[0])
    brain = Brain(clients, cfg["assembler"], cfg["default_provider"])
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(default_llm, cfg["assembler"]),
        "decay": DecaySystem(),
    }
    return World(cfg["world"], systems), brain, systems


def get_autonomous_agents(world: World) -> list:
    """Return entities that have AgentLayer and are autonomous."""
    return [e for e in world.entities.values()
            if e.has("agent") and e.get("agent").autonomous]
