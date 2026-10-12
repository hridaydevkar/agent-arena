from arena_server.engine import Engine
from arena_server.store import Store


def test_persistence_and_interrupted_job(tmp_path, monkeypatch):
    monkeypatch.setenv("ARENA_DATA_DIR", str(tmp_path))
    store = Store()
    store.put("agents", {"id": "example", "name": "Example"})
    store.put("jobs", {"id": "unfinished", "status": "running"})
    reconnected = Store()
    assert reconnected.get("agents", "example")["name"] == "Example"
    engine = Engine(reconnected)
    assert reconnected.get("jobs", "unfinished")["status"] == "interrupted"
    engine.pool.shutdown()
