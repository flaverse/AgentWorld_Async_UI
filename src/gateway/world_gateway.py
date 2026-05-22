"""WorldGateway — external agent session manager with permissions.
Zero cognitive code — pure lifecycle + access control.
"""

import secrets

from core.session import SessionManager


def _generate_key() -> str:
    return secrets.token_hex(16)


class PermissionError(Exception):
    pass


class WorldGateway:
    def __init__(self, world, director, persist_dir="/tmp/agent_memories"):
        self.world = world
        self.director = director
        self.session_manager = SessionManager(world, director, persist_dir)
        self._session_keys: dict[str, str] = {}   # agent_id → api_key
        self._admin_keys: set[str] = set()

    def _check_owner(self, agent_id: str, api_key: str = ""):
        if agent_id not in self._session_keys:
            raise PermissionError(f"no session for {agent_id}")
        if api_key and api_key != self._session_keys[agent_id]:
            raise PermissionError(f"wrong key for {agent_id}")

    def _check_admin(self, api_key: str = ""):
        if api_key and api_key not in self._admin_keys:
            raise PermissionError("admin required")

    # ── Public API ──

    def join(self, agent_id: str, agent_def: dict,
             api_key: str = "", is_admin: bool = False) -> dict:
        """Spawn external agent and take control. Returns session info."""
        # Ownership check: existing session owned by different key → denied
        if agent_id in self._session_keys:
            if api_key and api_key != self._session_keys[agent_id]:
                raise PermissionError(f"session {agent_id} owned by another key")
            # Same key → rejoin (agent despawned? re-spawn)
            self.session_manager.leave(agent_id)

        session = self.session_manager.join(agent_id, agent_def)
        key = api_key or _generate_key()
        self._session_keys[agent_id] = key
        if is_admin:
            self._admin_keys.add(key)
        return {
            "session_id": agent_id,
            "session_key": key,
            "name": session.entity.name,
            "zone": session.entity.zone,
        }

    def perceive(self, agent_id: str, api_key: str = "") -> dict:
        self._check_owner(agent_id, api_key)
        sess = self.session_manager.sessions.get(agent_id)
        if not sess:
            raise PermissionError(f"no active session for {agent_id}")
        return sess.perceive()

    def act(self, agent_id: str, decision: dict, api_key: str = ""):
        self._check_owner(agent_id, api_key)
        sess = self.session_manager.sessions.get(agent_id)
        if not sess:
            raise PermissionError(f"no active session for {agent_id}")
        sess.act(decision)

    def leave(self, agent_id: str, api_key: str = "") -> dict:
        self._check_owner(agent_id, api_key)
        self._session_keys.pop(agent_id, None)
        return self.session_manager.leave(agent_id)

    # ── Admin ──

    def freeze(self, api_key: str = ""):
        self._check_admin(api_key)
        self.director.freeze()

    def unfreeze(self, api_key: str = ""):
        self._check_admin(api_key)
        self.director.unfreeze()

    def kick(self, agent_id: str, api_key: str = ""):
        self._check_admin(api_key)
        self._session_keys.pop(agent_id, None)
        return self.session_manager.leave(agent_id)

    def list_sessions(self, api_key: str = "") -> list:
        self._check_admin(api_key)
        return [{
            "agent_id": aid,
            "name": self.world.entities.get(aid, None).name if aid in self.world.entities else "despawned",
        } for aid in self._session_keys]
