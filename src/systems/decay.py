class DecaySystem:
    def tick(self, agent, elapsed_minutes: float) -> None:
        if not agent.has("agent"):
            return
        agent_layer = agent.get("agent")
        if not agent_layer.drives:
            return
        agent_layer.drives.decay(elapsed_minutes)
