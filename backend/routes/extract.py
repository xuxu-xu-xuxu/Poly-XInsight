from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import select, func
from backend.models.database import get_db, Paper, Entity
from backend.services.extract_service import run_extraction
from backend.services.solid_electrolyte import extract_solid_electrolyte_records
from backend.services.solid_electrolyte_properties.mining import mine_solid_electrolyte_properties
from backend.services.thermal_conductive_properties.mining import mine_thermal_conductive_properties

router = APIRouter(prefix="/api", tags=["extract"])


@router.post("/extract/{paper_id}")
async def trigger_extraction(paper_id: str, background_tasks: BackgroundTasks):
    async for db in get_db():
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        if not paper.full_text:
            raise HTTPException(status_code=400, detail="Paper has no text content")
        break

    background_tasks.add_task(run_extraction, paper_id, paper.full_text)
    return {"paper_id": paper_id, "status": "extraction_started"}


@router.get("/extract/{paper_id}/status")
async def extraction_status(paper_id: str):
    async for db in get_db():
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        count_result = await db.execute(
            select(func.count()).select_from(Entity).where(Entity.paper_id == paper_id)
        )
        count = count_result.scalar()
        break
    return {"paper_id": paper_id, "status": "done" if count > 0 else "pending", "entity_count": count}


@router.post("/extract/solid-electrolyte/{paper_id}")
async def trigger_solid_electrolyte_extraction(paper_id: str):
    async for db in get_db():
        paper = await db.get(Paper, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        if not paper.full_text:
            raise HTTPException(status_code=400, detail="Paper has no text content")
        full_text = paper.full_text
        break
    return await extract_solid_electrolyte_records(paper_id, full_text)


@router.post("/extract/solid-electrolyte/properties/mine")
async def trigger_solid_electrolyte_property_mining(
    background_tasks: BackgroundTasks,
    replace: bool = Query(default=True),
    limit_per_query: int = Query(default=40, ge=5, le=200),
):
    background_tasks.add_task(mine_solid_electrolyte_properties, replace, limit_per_query)
    return {"status": "solid_electrolyte_property_mining_started"}


@router.post("/extract/thermal-conductive/properties/mine")
async def trigger_thermal_conductive_property_mining(
    background_tasks: BackgroundTasks,
    replace: bool = Query(default=True),
    limit_per_query: int = Query(default=40, ge=5, le=500),
):
    background_tasks.add_task(mine_thermal_conductive_properties, replace, limit_per_query)
    return {"status": "thermal_conductive_property_mining_started"}
