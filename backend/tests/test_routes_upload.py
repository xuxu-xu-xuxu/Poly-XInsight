import asyncio

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import Paper

client = TestClient(app)


def test_upload_no_file():
    resp = client.post("/api/upload")
    assert resp.status_code == 422


def test_process_paper_marks_failed_when_ingest_raises(monkeypatch):
    from backend.routes import upload as upload_route

    paper = Paper(id="paper-1", title="sample.pdf", file_path="/tmp/sample.pdf", status="processing")

    class FakeDB:
        def __init__(self):
            self.paper = paper
            self.committed = False

        async def get(self, model, key):
            if model is Paper and key == self.paper.id:
                return self.paper
            return None

        async def commit(self):
            self.committed = True

    fake_db = FakeDB()

    async def fake_get_db():
        yield fake_db

    async def fake_ingest_pdf(_path):
        raise RuntimeError("embedding timeout")

    monkeypatch.setattr(upload_route, "get_db", fake_get_db)
    monkeypatch.setattr(upload_route, "ingest_pdf", fake_ingest_pdf)

    asyncio.run(upload_route._process_paper("paper-1", "/tmp/sample.pdf"))

    assert paper.status == "failed"
    assert fake_db.committed is True
