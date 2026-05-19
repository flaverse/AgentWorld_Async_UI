"""SQLite persistence for agent state snapshots and interactions."""
import sqlite3, time, uuid


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

    def close(self):
        self.conn.close()
