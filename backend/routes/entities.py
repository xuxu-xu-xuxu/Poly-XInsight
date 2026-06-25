from fastapi import APIRouter, Query
from sqlalchemy import select
from backend.models.database import EntitySynonym, get_db
from backend.services.entity_mining import mine_entities
from backend.services.schema_convergence import run_schema_convergence
from backend.services.topic_navigation import load_topic_cards

router = APIRouter(prefix="/api", tags=["entities"])


@router.get("/entities")
async def query_entities(
    domain_id: str | None = Query(default=None),
    topic_limit: int = Query(default=8, ge=1, le=20),
    papers_per_topic: int = Query(default=4, ge=1, le=8),
):
    return await load_topic_cards(
        domain_id=domain_id,
        max_topics=topic_limit,
        papers_per_topic=papers_per_topic,
    )

@router.get("/entities/types")
async def list_entity_types():
    return {"types": ["topic", "paper", "material", "method", "problem", "property"]}

@router.get("/entities/synonyms")
async def list_synonyms():
    async for db in get_db():
        result = await db.execute(select(EntitySynonym))
        synonyms = [{"canonical": s.canonical, "variant": s.variant} for s in result.scalars().all()]
        break
    return {"synonyms": synonyms}

@router.post("/entities/converge")
async def trigger_convergence():
    result = await run_schema_convergence()
    return result


@router.post("/entities/mine")
async def trigger_entity_mining(
    domain_id: str | None = None,
    replace: bool = True,
    paper_limit: int | None = None,
    chunk_limit: int = 10000,
):
    return await mine_entities(
        domain_id=domain_id,
        replace=replace,
        paper_limit=paper_limit,
        chunk_limit=chunk_limit,
    )
