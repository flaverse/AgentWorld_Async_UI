"""SessionManager — external agent lifecycle.

Join: spawn entity, restore prior memory, take control.
Leave: save memory, despawn entity, release control.
"""
import os, json


class ExternalAgentSession:
    def __init__(self, entity, director):
        self.entity = entity
        self.director = director

    def perceive(self) -> dict:
        return self.director.snap(self.entity.id)

    def act(self, decision: dict):
        self.director.order(self.entity.id, decision)


class SessionManager:
    def __init__(self, world, director, persist_dir="/tmp/agent_memories"):
        self.world = world
        self.director = director
        self.persist_dir = persist_dir
        self.sessions: dict[str, ExternalAgentSession] = {}
        os.makedirs(persist_dir, exist_ok=True)

    def _memory_path(self, agent_id: str) -> str:
        return os.path.join(self.persist_dir, f"{agent_id}.json")

    def join(self, agent_id: str, agent_def: dict) -> ExternalAgentSession:
        """Spawn external agent. Restore prior memory if same ID existed before."""
        path = self._memory_path(agent_id)
        prior_memory = []
        if os.path.exists(path):
            try:
                with open(path) as f:
                    prior_memory = json.load(f)
            except Exception:
                pass

        entity = self.world.spawn_entity(agent_def)

        if prior_memory:
            for entry in prior_memory:
                entity.get("agent").memory.record(entry["text"], ts=entry.get("ts", 0))

        self.director.take(agent_id)
        session = ExternalAgentSession(entity, self.director)
        self.sessions[agent_id] = session
        return session

    def leave(self, agent_id: str) -> dict:
        """Despawn agent, save memory, release."""
        session = self.sessions.pop(agent_id, None)
        if not session:
            return {}
        al = session.entity.get("agent")
        memory = [{"ts": e["ts"], "text": e["text"]} for e in al.memory.entries] if al else []

        with open(self._memory_path(agent_id), "w") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

        self.director.release(agent_id)
        self.world.despawn_entity(agent_id)
        return {"agent_id": agent_id, "memory": memory}
