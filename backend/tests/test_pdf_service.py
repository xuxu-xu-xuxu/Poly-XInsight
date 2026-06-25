import os
from backend.services.pdf_service import compute_paper_id, save_upload

def test_compute_paper_id_deterministic(tmp_path):
    f = tmp_path / "test.pdf"
    f.write_text("hello world")
    id1 = compute_paper_id(str(f))
    id2 = compute_paper_id(str(f))
    assert id1 == id2
    assert len(id1) == 16

def test_save_upload_creates_file(tmp_path):
    path = save_upload(b"fake pdf", "test.pdf", str(tmp_path))
    assert os.path.exists(path)
    assert "test.pdf" in os.path.basename(path)
