from pathlib import Path

from backend.models.schemas import DownloadCreate, DownloadIngestRequest
from backend.services.download_service import _normalize_strategy, _validate_downloaded_pdf


def test_download_create_defaults_to_legal_only():
    request = DownloadCreate(identifier="10.1038/example")

    assert request.strategy == "legal_only"


def test_download_ingest_requires_domain():
    request = DownloadIngestRequest(domain_id="solid-state")

    assert request.domain_id == "solid-state"


def test_validate_downloaded_pdf_stays_in_download_dir(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7")

    assert _validate_downloaded_pdf(str(pdf), str(tmp_path)) == str(pdf.resolve())


def test_unknown_download_strategy_falls_back_to_legal_only():
    assert _normalize_strategy("scihub_only", "legal_only") == "legal_only"
