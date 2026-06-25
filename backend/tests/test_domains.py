import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from backend.main import app
from backend.models.database import LibraryDomain, PaperDomainAssignment, Paper


client = TestClient(app)


def test_library_domain_models_exist():
    assert inspect(LibraryDomain).tables[0].name == "library_domains"
    assert inspect(PaperDomainAssignment).tables[0].name == "paper_domain_assignments"


def test_get_domains_returns_tiles():
    from backend.routes import domains as domains_route

    async def fake_seed():
        return None

    async def fake_list():
        return [
            {"id": "solid-state", "name": "固态电池", "paper_count": 3, "ingested_count": 2, "processing_count": 1, "failed_count": 0},
            {"id": "unclassified", "name": "未分类", "paper_count": 1, "ingested_count": 1, "processing_count": 0, "failed_count": 0},
        ]

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(domains_route, "seed_default_domains_if_needed", fake_seed)
    monkeypatch.setattr(domains_route, "list_library_domains", fake_list)
    resp = client.get("/api/domains")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all("id" in item and "name" in item and "paper_count" in item for item in data)
    monkeypatch.undo()


def test_create_domain_duplicate_returns_400(monkeypatch):
    from backend.routes import domains as domains_route

    async def fake_create(payload):
        raise ValueError("Domain already exists")

    monkeypatch.setattr(domains_route, "create_library_domain", fake_create)

    resp = client.post("/api/domains", json={"id": "solid-state", "name": "固态电池"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Domain already exists"


def test_delete_default_domain_returns_400(monkeypatch):
    from backend.routes import domains as domains_route

    async def fake_delete(domain_id):
        raise ValueError("Default domains cannot be deleted")

    monkeypatch.setattr(domains_route, "delete_library_domain", fake_delete)

    resp = client.delete("/api/domains/unclassified")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Default domains cannot be deleted"


def test_delete_domain_returns_reassignment_summary(monkeypatch):
    from backend.routes import domains as domains_route

    async def fake_delete(domain_id):
        return {"deleted": domain_id, "reassigned_to": "unclassified", "paper_count": 3}

    monkeypatch.setattr(domains_route, "delete_library_domain", fake_delete)

    resp = client.delete("/api/domains/custom-domain")

    assert resp.status_code == 200
    assert resp.json() == {"deleted": "custom-domain", "reassigned_to": "unclassified", "paper_count": 3}


def test_upload_accepts_domain_id(monkeypatch, tmp_path):
    from backend.routes import upload as upload_route

    class FakeResult:
        def __init__(self, value=None):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class FakeDB:
        def __init__(self):
            self.added = []
            self.committed = False
            self.paper = None
            self.domain = type("Domain", (), {"id": "solid-state"})()

        async def get(self, model, key):
            if model is Paper:
                return self.paper if self.paper and self.paper.id == key else None
            if model is LibraryDomain:
                if key in ("solid-state", "unclassified"):
                    return self.domain
            return None

        async def execute(self, *args, **kwargs):
            return FakeResult()

        def add(self, obj):
            self.added.append(obj)
            if isinstance(obj, Paper):
                self.paper = obj

        async def commit(self):
            self.committed = True

    fake_db = FakeDB()

    async def fake_get_db():
        yield fake_db

    monkeypatch.setattr(upload_route, "get_db", fake_get_db)
    monkeypatch.setattr(upload_route, "save_upload", lambda content, filename, upload_dir: str(tmp_path / filename))
    monkeypatch.setattr(upload_route, "compute_paper_id", lambda path: "paper-1")
    async def fake_ingest_pdf(path):
        return {"title": "Sample Title", "full_text": "body"}
    monkeypatch.setattr(upload_route, "ingest_pdf", fake_ingest_pdf)

    file_data = {"file": ("sample.pdf", b"%PDF-1.4 fake", "application/pdf")}
    resp = client.post("/api/upload", files=file_data, data={"domain_id": "solid-state"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"
    assert fake_db.committed is True
    assert any(isinstance(item, Paper) for item in fake_db.added)
    assert any(getattr(item, "domain_id", None) == "solid-state" for item in fake_db.added)
