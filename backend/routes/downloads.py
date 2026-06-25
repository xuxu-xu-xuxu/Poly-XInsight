from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select

from backend.config import get_settings
from backend.models.database import (
    DownloadedPaper,
    LibraryDomain,
    Paper,
    PaperDomainAssignment,
    get_db,
)
from backend.models.schemas import DownloadCreate, DownloadIngestRequest, DownloadedPaperOut
from backend.services.domain_service import set_paper_domain
from backend.services.download_service import download_pdf
from backend.services.pdf_service import compute_paper_id

router = APIRouter(prefix="/api", tags=["downloads"])


def _download_to_out(download: DownloadedPaper) -> DownloadedPaperOut:
    return DownloadedPaperOut.model_validate(download)


@router.get("/downloads")
async def list_downloads():
    async for db in get_db():
        result = await db.execute(
            select(DownloadedPaper).order_by(DownloadedPaper.created_at.desc()).limit(50)
        )
        downloads = result.scalars().all()
        return {"items": [_download_to_out(item) for item in downloads]}


@router.post("/downloads")
async def create_download(request: DownloadCreate, background_tasks: BackgroundTasks):
    async for db in get_db():
        download = DownloadedPaper(
            identifier=request.identifier.strip(),
            strategy=request.strategy,
            status="downloading",
        )
        db.add(download)
        await db.commit()
        await db.refresh(download)
        background_tasks.add_task(_run_download_job, download.id)
        return _download_to_out(download)


@router.post("/downloads/{download_id}/ingest")
async def ingest_download(download_id: str, request: DownloadIngestRequest, background_tasks: BackgroundTasks):
    async for db in get_db():
        download = await db.get(DownloadedPaper, download_id)
        if not download:
            raise HTTPException(status_code=404, detail="Download not found")
        if download.status not in ("downloaded", "ingested", "failed"):
            raise HTTPException(status_code=400, detail="Download is not ready to ingest")
        if not download.file_path:
            raise HTTPException(status_code=400, detail="Downloaded PDF file is missing")

        domain = await db.get(LibraryDomain, request.domain_id)
        if not domain:
            raise HTTPException(status_code=400, detail="Domain not found")

        paper_id = compute_paper_id(download.file_path)
        existing = await db.get(Paper, paper_id)
        if existing:
            download.paper_id = paper_id
            download.status = "ingested"
            await db.commit()
            await set_paper_domain(paper_id, domain.id)
            await db.refresh(download)
            return _download_to_out(download)

        title = download.title or download.doi or download.identifier
        db.add(Paper(id=paper_id, title=title, file_path=download.file_path, status="processing"))
        db.add(PaperDomainAssignment(paper_id=paper_id, domain_id=domain.id))
        download.paper_id = paper_id
        download.status = "ingesting"
        download.error = None
        await db.commit()
        await db.refresh(download)
        background_tasks.add_task(_process_downloaded_paper, download.id, paper_id, download.file_path, request.auto_mine)
        return _download_to_out(download)


async def _run_download_job(download_id: str):
    settings = get_settings()
    async for db in get_db():
        download = await db.get(DownloadedPaper, download_id)
        if not download:
            return
        identifier = download.identifier
        strategy = download.strategy
        break

    try:
        result = await download_pdf(
            identifier,
            settings.scansci_download_dir,
            strategy,
            settings.scansci_download_strategy,
        )
        async for db in get_db():
            download = await db.get(DownloadedPaper, download_id)
            if download:
                download.doi = result.get("doi") or result.get("identifier")
                download.title = result.get("title")
                download.source = result.get("source")
                download.file_path = result.get("file")
                download.status = "downloaded"
                download.error = None
                await db.commit()
            break
    except Exception as exc:
        async for db in get_db():
            download = await db.get(DownloadedPaper, download_id)
            if download:
                download.status = "failed"
                download.error = str(exc)
                await db.commit()
            break


async def _process_downloaded_paper(download_id: str, paper_id: str, file_path: str, auto_mine: bool):
    try:
        from backend.routes.upload import _process_paper

        await _process_paper(paper_id, file_path, auto_mine)
        async for db in get_db():
            download = await db.get(DownloadedPaper, download_id)
            if download:
                download.status = "ingested"
                download.error = None
                await db.commit()
            break
    except Exception as exc:
        async for db in get_db():
            download = await db.get(DownloadedPaper, download_id)
            paper = await db.get(Paper, paper_id)
            error = str(exc) or repr(exc)
            if download:
                download.status = "failed"
                download.error = error
            if paper:
                paper.status = "failed"
            await db.commit()
            break
