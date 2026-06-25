from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_extract_paper_not_found():
    resp = client.post("/api/extract/nonexistent")
    assert resp.status_code == 404


def test_visualize_empty_request():
    resp = client.post("/api/visualize", json={"query": ""})
    assert resp.status_code in (200, 400, 404, 422, 500)


def test_entities_empty():
    resp = client.get("/api/entities")
    assert resp.status_code in (200, 404)
