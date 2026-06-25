from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_list_papers_empty():
    resp = client.get("/api/papers")
    assert resp.status_code in (200, 404)


def test_get_paper_not_found():
    resp = client.get("/api/papers/nonexistent")
    assert resp.status_code in (404,)
