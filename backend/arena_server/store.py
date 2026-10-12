import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class Store:
    def __init__(self):
        root = Path(os.getenv("ARENA_DATA_DIR", ".arena"))
        from .provider import read_only

        # Public mode never opens the private workspace database by accident.
        if read_only():
            root = root / "public-readonly"
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "arena.db"
        self.lock = threading.RLock()
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self):
        with self.lock:
            conn = sqlite3.connect(self.path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def put(self, table, item):
        assert table in ("agents", "runs", "jobs")
        with self.connection() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {table}(id,data) VALUES (?,?)", (item["id"], json.dumps(item, allow_nan=False))
            )
        return item

    def get(self, table, id):
        assert table in ("agents", "runs", "jobs")
        with self.connection() as conn:
            row = conn.execute(f"SELECT data FROM {table} WHERE id=?", (id,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, table):
        assert table in ("agents", "runs", "jobs")
        with self.connection() as conn:
            rows = conn.execute(f"SELECT data FROM {table} ORDER BY rowid DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def initialized(self):
        with self.connection() as conn:
            return bool(conn.execute("SELECT 1 FROM meta WHERE key='seed-v1'").fetchone())

    def mark_initialized(self):
        with self.connection() as conn:
            conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('seed-v1','true')")

    def replace_public(self, agents, runs):
        from .provider import read_only

        if not read_only():
            raise ValueError("Snapshot replacement is allowed only in an isolated public store")
        with self.connection() as conn:
            for table in ("agents", "runs", "jobs", "meta"):
                conn.execute(f"DELETE FROM {table}")
            for table, rows in (("agents", agents), ("runs", runs)):
                conn.executemany(
                    f"INSERT INTO {table}(id,data) VALUES (?,?)",
                    [(row["id"], json.dumps(row, allow_nan=False)) for row in rows],
                )
        self.mark_initialized()
