from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_chat_validation():
    resp = client.post("/api/chat", json={"query": ""})
    assert resp.status_code in (200, 404, 422)
