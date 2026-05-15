"""SQLite persistence for agent state snapshots and interactions."""
import sqlite3, json, time, uuid


class WorldDB:
    def __init__(self, path: str = "world.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id    TEXT PRIMARY KEY,
                started   REAL,
                ended     REAL,
                world_name TEXT
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                run_id    TEXT,
                tick      INTEGER,
                entity_id TEXT,
                name      TEXT,
                zone      TEXT,
                pos_x     INT,
                pos_y     INT,
                drives    TEXT,
                PRIMARY KEY (run_id, tick, entity_id)
            );
            CREATE TABLE IF NOT EXISTS interactions (
                run_id    TEXT,
                tick      REAL,
                agent     TEXT,
                target    TEXT,
                action    TEXT,
                narrative TEXT,
                deltas    TEXT
            );
        """)

    def start_run(self, world_name: str = "") -> str:
        run_id = uuid.uuid4().hex[:12]
        self.conn.execute("INSERT INTO runs(run_id,started,world_name) VALUES(?,?,?)",
                          (run_id, time.time(), world_name))
        self.conn.commit()
        return run_id

    def end_run(self, run_id: str):
        self.conn.execute("UPDATE runs SET ended=? WHERE run_id=?",
                          (time.time(), run_id))
        self.conn.commit()

    def snapshot(self, run_id: str, tick: int, agents: list):
        for a in agents:
            drives_json = json.dumps(
                {k: round(float(v), 1) for k, v in
                 a.get("agent").drives.attrs.items()}, ensure_ascii=False)
            self.conn.execute(
                "INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?,?,?,?,?)",
                (run_id, tick, a.id, a.name, a.zone, a.pos[0], a.pos[1],
                 drives_json))
        self.conn.commit()

    def log_interaction(self, run_id: str, agent_name: str, target_name: str,
                        action: str, narrative: str, deltas: dict):
        self.conn.execute(
            "INSERT INTO interactions VALUES(?,?,?,?,?,?,?)",
            (run_id, time.time(), agent_name, target_name, action,
             narrative, json.dumps(deltas, ensure_ascii=False)))
        self.conn.commit()

    def close(self):
        self.conn.close()
