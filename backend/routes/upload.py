import logging
import os
import uuid
import zipfile

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Form, HTTPException
from sqlalchemy import select

from backend.models.database import get_db, IngestionJob, Paper, PaperDomainAssignment, PaperProcessingTask, LibraryDomain
from backend.services.pdf_service import save_upload, save_upload_stream, compute_paper_id
from backend.services.ingestion import ingest_pdf
from backend.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_mine: bool = Form(default=False),
    domain_id: str = Form(default="thermal-polymer"),
):
    settings = get_settings()
    file_path = await save_upload_stream(file, settings.upload_dir)
    paper_id = compute_paper_id(file_path)

    async for db in get_db():
        existing = await db.get(Paper, paper_id)
        if existing:
            return {"paper_id": paper_id, "status": "duplicate", "message": "Paper already exists"}
        domain = await db.get(LibraryDomain, domain_id) or await db.get(LibraryDomain, "thermal-polymer")
        if not domain:
            raise HTTPException(status_code=400, detail="Domain not found")
        db.add(Paper(id=paper_id, title=file.filename, file_path=file_path, status="processing"))
        db.add(PaperDomainAssignment(paper_id=paper_id, domain_id=domain.id))
        await db.commit()
        break

    background_tasks.add_task(_process_paper, paper_id, file_path, auto_mine)
    return {"paper_id": paper_id, "status": "processing"}


@router.post("/upload/batch")
async def upload_batch(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_mine: bool = Form(default=False),
    domain_id: str = Form(default="thermal-polymer"),
):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Batch upload expects a .zip file of PDFs")
    settings = get_settings()
    job_id = uuid.uuid4().hex
    job_dir = os.path.join(settings.upload_dir, "jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)
    zip_path = await save_upload_stream(file, job_dir)

    # Create job record immediately, extraction happens in background
    async for db in get_db():
        db.add(IngestionJob(id=job_id, status="extracting", total=0))
        await db.commit()
        break

    background_tasks.add_task(_process_batch, job_id, zip_path, auto_mine, domain_id)
    return {"job_id": job_id, "status": "extracting", "total": 0}


@router.get("/ingestion/jobs")
async def list_ingestion_jobs():
    async for db in get_db():
        result = await db.execute(select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(50))
        jobs = result.scalars().all()
        break
    return {"items": [_job_to_dict(job) for job in jobs]}


@router.get("/ingestion/jobs/{job_id}")
async def get_ingestion_job(job_id: str):
    async for db in get_db():
        job = await db.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        tasks_result = await db.execute(select(PaperProcessingTask).where(PaperProcessingTask.job_id == job_id))
        tasks = tasks_result.scalars().all()
        break
    data = _job_to_dict(job)
    data["tasks"] = [
        {
            "id": task.id,
            "paper_id": task.paper_id,
            "filename": task.filename,
            "status": task.status,
            "stage": task.stage,
            "error": task.error,
        }
        for task in tasks
    ]
    return data


@router.post("/ingestion/jobs/{job_id}/pause")
async def pause_ingestion_job(job_id: str):
    async for db in get_db():
        job = await db.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status in ("extracting", "queued", "running"):
            job.status = "paused"
            await db.commit()
        break
    return {"job_id": job_id, "status": "paused"}


@router.post("/ingestion/jobs/{job_id}/resume")
async def resume_ingestion_job(job_id: str, background_tasks: BackgroundTasks):
    async for db in get_db():
        job = await db.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "paused":
            raise HTTPException(status_code=400, detail="Only paused jobs can be resumed")

        # Find remaining queued tasks
        result = await db.execute(
            select(PaperProcessingTask.filename)
            .where(PaperProcessingTask.job_id == job_id)
            .where(PaperProcessingTask.status.in_(["queued", "running"]))
        )
        remaining_filenames = [row[0] for row in result.all()]
        break

    if not remaining_filenames:
        raise HTTPException(status_code=400, detail="No remaining tasks to resume")

    # Find the ZIP file for this job and re-trigger processing
    import zipfile, os, uuid
    settings = get_settings()
    job_dir = os.path.join(settings.upload_dir, "jobs", job_id)
    # Find the ZIP file
    zip_files = [f for f in os.listdir(job_dir) if f.lower().endswith(".zip")] if os.path.isdir(job_dir) else []
    if not zip_files:
        raise HTTPException(status_code=400, detail="Original ZIP file not found, cannot resume")

    zip_path = os.path.join(job_dir, zip_files[0])
    # Re-trigger batch processing (it will skip already-processed PDFs)
    background_tasks.add_task(_process_batch, job_id, zip_path, False, "thermal-polymer")
    return {"job_id": job_id, "status": "running", "message": f"Resuming {len(remaining_filenames)} remaining tasks"}


@router.delete("/ingestion/jobs/{job_id}")
async def cancel_ingestion_job(job_id: str):
    async for db in get_db():
        job = await db.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status in ("extracting", "queued", "running", "paused"):
            job.status = "cancelled"
            # Mark remaining queued tasks as cancelled
            tasks_result = await db.execute(
                select(PaperProcessingTask).where(
                    PaperProcessingTask.job_id == job_id,
                    PaperProcessingTask.status == "queued",
                )
            )
            for task in tasks_result.scalars().all():
                task.status = "cancelled"
            await db.commit()
        elif job.status in ("done", "partial_failed", "failed", "cancelled"):
            # Hard-delete completed/failed/cancelled jobs and their tasks
            tasks_result = await db.execute(
                select(PaperProcessingTask).where(
                    PaperProcessingTask.job_id == job_id,
                )
            )
            for task in tasks_result.scalars().all():
                await db.delete(task)
            await db.delete(job)
            await db.commit()
            # Clean up job directory (ZIP + extracted PDFs not referenced by any Paper)
            _cleanup_job_files(job_id)
        break
    return {"job_id": job_id, "status": "cancelled"}


async def _process_paper(paper_id: str, file_path: str, auto_mine: bool = False):
    from backend.services.extract_service import run_extraction
    from backend.services.solid_electrolyte import extract_solid_electrolyte_records

    try:
        result = await ingest_pdf(file_path)
    except Exception:
        logger.exception("Failed to ingest uploaded paper %s from %s", paper_id, file_path)
        async for db in get_db():
            paper = await db.get(Paper, paper_id)
            if paper:
                paper.status = "failed"
                await db.commit()
            break
        raise

    async for db in get_db():
        paper = await db.get(Paper, paper_id)
        if paper:
            doc_title = (result.get("title") or "").strip()
            if doc_title:
                paper.title = doc_title
            paper.authors = result.get("authors")
            paper.year = result.get("year")
            paper.journal = result.get("journal")
            paper.abstract = result.get("abstract")
            paper.full_text = result["full_text"]
            paper.status = "ingested"
            await db.commit()
        break

    if auto_mine and result.get("full_text"):
        await extract_solid_electrolyte_records(paper_id, result["full_text"])

    # keep the legacy dynamic extractor behind the explicit auto_mine switch
    if auto_mine and result.get("full_text"):
        try:
            await run_extraction(paper_id, result["full_text"])
        except Exception:
            pass
    # keep PDF file on disk for reference


async def _process_batch(job_id: str, zip_path: str, auto_mine: bool, domain_id: str):
    # Phase 1: Extract PDFs from ZIP
    pdf_paths: list[str] = []
    orphan_paths: list[str] = []  # extracted PDFs that turned out to be duplicates, safe to delete
    try:
        with zipfile.ZipFile(zip_path) as archive:
            items = [i for i in archive.infolist() if not i.is_dir() and i.filename.lower().endswith(".pdf")]
            total = len(items)

            async for db in get_db():
                job = await db.get(IngestionJob, job_id)
                if job:
                    job.status = "extracting"
                    job.total = total
                    job.current_file = f"正在解压 {total} 个文件..."
                await db.commit()
                break

            job_dir = os.path.dirname(zip_path)
            for item in items:
                original_name = os.path.basename(item.filename) or "paper.pdf"
                target = os.path.join(job_dir, f"{uuid.uuid4().hex}_{original_name}")
                with archive.open(item) as source, open(target, "wb") as dest:
                    dest.write(source.read())
                pdf_paths.append(target)
    except zipfile.BadZipFile:
        async for db in get_db():
            job = await db.get(IngestionJob, job_id)
            if job:
                job.status = "failed"
                job.error = "Invalid zip file"
            await db.commit()
            break
        return

    if not pdf_paths:
        async for db in get_db():
            job = await db.get(IngestionJob, job_id)
            if job:
                job.status = "failed"
                job.error = "No PDF files found in zip"
            await db.commit()
            break
        return

    # Phase 2: Create tasks and start processing
    async for db in get_db():
        job = await db.get(IngestionJob, job_id)
        if job:
            job.status = "running"
            job.current_file = None
        for path in pdf_paths:
            db.add(PaperProcessingTask(job_id=job_id, filename=os.path.basename(path), status="queued"))
        await db.commit()
        break

    for path in pdf_paths:
        # Check if job was paused or cancelled
        async for db in get_db():
            job = await db.get(IngestionJob, job_id)
            if job and job.status in ("paused", "cancelled"):
                break
        if job and job.status in ("paused", "cancelled"):
            break

        filename = os.path.basename(path)

        # Skip files already done in a previous run (resume support)
        async for db in get_db():
            existing_task = (await db.execute(
                select(PaperProcessingTask)
                .where(PaperProcessingTask.job_id == job_id)
                .where(PaperProcessingTask.filename == filename)
                .where(PaperProcessingTask.status.in_(["done", "duplicate"]))
                .limit(1)
            )).scalar_one_or_none()
            if existing_task:
                break
        if existing_task:
            continue

        async for db in get_db():
            job = await db.get(IngestionJob, job_id)
            task_result = await db.execute(
                select(PaperProcessingTask)
                .where(PaperProcessingTask.job_id == job_id)
                .where(PaperProcessingTask.filename == filename)
                .limit(1)
            )
            task = task_result.scalar_one_or_none()
            if job:
                job.current_file = filename
            if task:
                task.status = "running"
                task.stage = "hashing"
            await db.commit()
            break

        try:
            paper_id = compute_paper_id(path)
            duplicate = False
            async for db in get_db():
                existing = await db.get(Paper, paper_id)
                domain = await db.get(LibraryDomain, domain_id) or await db.get(LibraryDomain, "thermal-polymer")
                task = (await db.execute(
                    select(PaperProcessingTask)
                    .where(PaperProcessingTask.job_id == job_id)
                    .where(PaperProcessingTask.filename == filename)
                    .limit(1)
                )).scalar_one_or_none()
                if existing:
                    duplicate = True
                else:
                    db.add(Paper(id=paper_id, title=filename, file_path=path, status="processing"))
                    if domain:
                        db.add(PaperDomainAssignment(paper_id=paper_id, domain_id=domain.id))
                if task:
                    task.paper_id = paper_id
                    task.stage = "ingesting"
                await db.commit()
                break

            if duplicate:
                orphan_paths.append(path)  # No Paper record references this file
                async for db in get_db():
                    job = await db.get(IngestionJob, job_id)
                    task = (await db.execute(
                        select(PaperProcessingTask)
                        .where(PaperProcessingTask.job_id == job_id)
                        .where(PaperProcessingTask.filename == filename)
                        .limit(1)
                    )).scalar_one_or_none()
                    if job:
                        job.duplicate += 1
                    if task:
                        task.status = "duplicate"
                    await db.commit()
                    break
                continue

            await _process_paper(paper_id, path, auto_mine)
            async for db in get_db():
                job = await db.get(IngestionJob, job_id)
                task = (await db.execute(
                    select(PaperProcessingTask)
                    .where(PaperProcessingTask.job_id == job_id)
                    .where(PaperProcessingTask.filename == filename)
                    .limit(1)
                )).scalar_one_or_none()
                if job:
                    job.succeeded += 1
                if task:
                    task.status = "done"
                    task.stage = "done"
                await db.commit()
                break
        except Exception as exc:
            async for db in get_db():
                job = await db.get(IngestionJob, job_id)
                task = (await db.execute(
                    select(PaperProcessingTask)
                    .where(PaperProcessingTask.job_id == job_id)
                    .where(PaperProcessingTask.filename == filename)
                    .limit(1)
                )).scalar_one_or_none()
                if job:
                    job.failed += 1
                    job.error = str(exc)
                if task:
                    task.status = "failed"
                    task.error = str(exc)
                await db.commit()
                break

    async for db in get_db():
        job = await db.get(IngestionJob, job_id)
        if job:
            job.status = "done" if job.failed == 0 else "partial_failed"
            job.current_file = None
            await db.commit()
        break

    # Clean up temporary files to avoid disk bloat
    for path in orphan_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info("Cleaned up duplicate PDF: %s", path)
        except Exception as e:
            logger.warning("Failed to clean up duplicate PDF %s: %s", path, e)
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
            logger.info("Cleaned up batch ZIP: %s", zip_path)
    except Exception as e:
        logger.warning("Failed to clean up batch ZIP %s: %s", zip_path, e)


def _cleanup_job_files(job_id: str):
    """Sync wrapper: schedule async cleanup of orphan job files."""
    import asyncio

    async def _cleanup():
        # Collect file paths referenced by Paper records
        referenced: set[str] = set()
        async for db_sess in get_db():
            result = await db_sess.execute(
                select(Paper.file_path).where(Paper.file_path.like(f"%jobs/{job_id}%"))
            )
            for row in result.scalars().all():
                referenced.add(os.path.normpath(row))
            break

        settings = get_settings()
        job_dir = os.path.join(settings.upload_dir, "jobs", job_id)
        if not os.path.isdir(job_dir):
            return

        # Remove unreferenced files
        for root, dirs, files in os.walk(job_dir, topdown=False):
            for name in files:
                file_path = os.path.normpath(os.path.join(root, name))
                if file_path not in referenced:
                    try:
                        os.remove(file_path)
                        logger.info("Cleaned up orphan job file: %s", file_path)
                    except Exception as e:
                        logger.warning("Failed to remove %s: %s", file_path, e)
            if root != job_dir and not os.listdir(root):
                try:
                    os.rmdir(root)
                except Exception:
                    pass

        # Remove job directory if empty
        if os.path.isdir(job_dir) and not os.listdir(job_dir):
            try:
                os.rmdir(job_dir)
                logger.info("Removed empty job directory: %s", job_dir)
            except Exception as e:
                logger.warning("Failed to remove job directory %s: %s", job_dir, e)

    try:
        asyncio.ensure_future(_cleanup())
    except Exception:
        pass


def _job_to_dict(job: IngestionJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "total": job.total,
        "succeeded": job.succeeded,
        "failed": job.failed,
        "duplicate": job.duplicate,
        "current_file": job.current_file,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
