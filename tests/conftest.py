import pytest
from arena_server.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARENA_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ARENA_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(app) as client:
        yield client
