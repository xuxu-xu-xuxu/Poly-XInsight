import asyncio
import os
from pathlib import Path
from typing import Any


ALLOWED_STRATEGIES = {"legal_only", "oa_first", "fastest"}


def _normalize_strategy(strategy: str | None, default_strategy: str) -> str:
    selected = (strategy or default_strategy or "legal_only").strip()
    if selected not in ALLOWED_STRATEGIES:
        return "legal_only"
    return selected


def _validate_downloaded_pdf(file_path: str, download_dir: str) -> str:
    resolved_file = Path(file_path).resolve()
    resolved_dir = Path(download_dir).resolve()
    if resolved_dir not in resolved_file.parents and resolved_file != resolved_dir:
        raise RuntimeError("Downloaded file is outside the configured download directory")
    if not resolved_file.exists():
        raise RuntimeError("Download reported success but the PDF file was not found")
    if resolved_file.suffix.lower() != ".pdf":
        raise RuntimeError("Downloaded file is not a PDF")
    return str(resolved_file)


def _download_sync(identifier: str, download_dir: str, strategy: str) -> dict[str, Any]:
    try:
        from scansci_pdf.sources import download
    except ImportError as exc:
        raise RuntimeError("scansci-pdf is not installed in the backend environment") from exc

    os.makedirs(download_dir, exist_ok=True)
    result = download(
        identifier.strip(),
        output_dir=download_dir,
        strategy=strategy,
        scihub_enabled=None,
        use_tor=False,
        use_vpnsci=False,
        bibtex=False,
    )
    if not result.get("success"):
        raise RuntimeError(result.get("error") or "PDF download failed")

    file_path = result.get("file") or result.get("path")
    if not file_path:
        raise RuntimeError("Download reported success without a file path")

    result["file"] = _validate_downloaded_pdf(str(file_path), download_dir)
    return result


async def download_pdf(identifier: str, download_dir: str, strategy: str | None, default_strategy: str) -> dict[str, Any]:
    selected_strategy = _normalize_strategy(strategy, default_strategy)
    return await asyncio.to_thread(_download_sync, identifier, download_dir, selected_strategy)
