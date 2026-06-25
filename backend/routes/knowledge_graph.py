from fastapi import APIRouter, Query

from backend.services.topic_navigation import load_topic_graph

router = APIRouter(prefix="/api", tags=["knowledge-graph"])


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    domain_id: str | None = Query(default=None),
    limit: int = Query(default=90, ge=20, le=180),
):
    max_topics = max(4, min(12, limit // 10))
    papers_per_topic = max(2, min(6, limit // 24))
    return await load_topic_graph(
        domain_id=domain_id,
        max_topics=max_topics,
        papers_per_topic=papers_per_topic,
    )
