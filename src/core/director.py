"""Director — controlled mode for NPC agents.

Freeze/unfreeze world, take/release NPC control,
snap sensory state, inject external decisions.
All controlled-mode semantics in one place.
"""


class Director:
    def __init__(self, world):
        self.world = world
        self.frozen = False
        self._controlled: set[str] = set()
        self._orders: dict[str, dict] = {}

    def freeze(self):
        """Pause the world. All NPC loops sleep at Phase 1."""
        self.frozen = True

    def unfreeze(self):
        """Resume the world. Pending orders begin executing."""
        self.frozen = False

    def take(self, agent_id: str):
        """Take control of an NPC. Its loop will skip LLM decide."""
        self._controlled.add(agent_id)

    def release(self, agent_id: str):
        """Return an NPC to autonomous mode."""
        self._controlled.discard(agent_id)
        self._orders.pop(agent_id, None)

    def is_controlled(self, agent_id: str) -> bool:
        return agent_id in self._controlled

    def order(self, agent_id: str, decision: dict):
        """Inject a decision for a controlled NPC.
        The NPC will execute it on its next Phase 3.
        """
        self._orders[agent_id] = decision

    def pending(self, agent_id: str) -> dict | None:
        """Pop and return the pending order, or None."""
        return self._orders.pop(agent_id, None)

    def snap(self, agent_id: str) -> dict:
        """Return what an NPC currently perceives.
        Used by the operator to decide what to order.
        """
        agent = self.world.entities.get(agent_id)
        if not agent:
            return {}
        al = agent.get("agent")
        return {
            "name": agent.name,
            "zone": agent.zone,
            "pos": agent.pos,
            "drives": dict(al.drives.attrs) if al and al.drives else {},
            "memory": [e["text"] for e in al.memory.recent(5)] if al and al.memory else [],
            "sensory": al.sensory.channels if al and al.sensory else {},
            "main_thread": al.main_thread if al else "",
        }
