from sqlalchemy import delete, select

from backend.models.database import (
    Paper,
    PaperDomainAssignment,
    SolidElectrolyteProperty,
    get_db,
)
from backend.services.embedding import embed_single
from backend.services.ingestion import init_es, init_milvus
from backend.services.solid_electrolyte_properties.extractor import extract_property_candidates

SOLID_STATE_DOMAIN_ID = "solid-state"

PROPERTY_QUERIES = {
    "ionic_conductivity": [
        "solid electrolyte ionic conductivity S/cm temperature",
        "conductivity sigma S cm-1 electrolyte impedance EIS",
        "mS cm-1 S cm-1 Li solid electrolyte",
        "argyrodite garnet NASICON ionic conductivity",
    ],
    "electrochemical_window": [
        "solid electrolyte electrochemical stability window voltage Li/Li+",
        "oxidation stability reduction stability stable up to V lithium",
        "linear sweep voltammetry electrochemical window V",
        "stable voltage window versus Li Li+",
    ],
}

PROPERTY_PHRASES = {
    "ionic_conductivity": ["S cm", "S/cm", "mS cm", "mS/cm", "ionic conductivity", "impedance"],
    "electrochemical_window": ["electrochemical window", "stability window", "stable up to", "linear sweep"],
}


async def solid_state_paper_ids() -> list[str]:
    async for db in get_db():
        result = await db.execute(
            select(Paper.id)
            .join(PaperDomainAssignment, PaperDomainAssignment.paper_id == Paper.id)
            .where(PaperDomainAssignment.domain_id == SOLID_STATE_DOMAIN_ID)
            .where(Paper.status == "ingested")
        )
        return list(result.scalars().all())
    return []


def _es_candidates(paper_ids: list[str], query: str, size: int) -> list[dict]:
    es = init_es()
    body = {
        "query": {
            "bool": {
                "must": [{
                    "multi_match": {
                        "query": query,
                        "fields": ["text^2", "heading"],
                        "operator": "or",
                    }
                }],
                "filter": [{"terms": {"paper_id": paper_ids}}],
            }
        },
        "size": size,
        "_source": ["paper_id", "chunk_index", "heading", "text"],
    }
    response = es.search(index="paper_chunks", body=body)
    return [
        {
            "paper_id": hit["_source"]["paper_id"],
            "chunk_index": hit["_source"].get("chunk_index", 0),
            "heading": hit["_source"].get("heading", ""),
            "text": hit["_source"].get("text", ""),
            "source": "es",
        }
        for hit in response["hits"]["hits"]
    ]


def _es_phrase_candidates(paper_ids: list[str], property_name: str, size: int) -> list[dict]:
    es = init_es()
    should = [
        {"match_phrase": {"text": phrase}}
        for phrase in PROPERTY_PHRASES[property_name]
    ]
    body = {
        "query": {
            "bool": {
                "should": should,
                "minimum_should_match": 1,
                "filter": [{"terms": {"paper_id": paper_ids}}],
            }
        },
        "size": size,
        "_source": ["paper_id", "chunk_index", "heading", "text"],
    }
    response = es.search(index="paper_chunks", body=body)
    return [
        {
            "paper_id": hit["_source"]["paper_id"],
            "chunk_index": hit["_source"].get("chunk_index", 0),
            "heading": hit["_source"].get("heading", ""),
            "text": hit["_source"].get("text", ""),
            "source": "es_phrase",
        }
        for hit in response["hits"]["hits"]
    ]


async def _milvus_candidates(paper_ids: list[str], query: str, size: int) -> list[dict]:
    vector = await embed_single(query)
    ids_str = ", ".join(f'"{paper_id}"' for paper_id in paper_ids)
    collection = init_milvus()
    results = collection.search(
        data=[vector],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
        limit=size,
        output_fields=["paper_id", "text", "heading", "chunk_index"],
        expr=f"paper_id in [{ids_str}]",
    )
    return [
        {
            "paper_id": hit.entity.get("paper_id"),
            "chunk_index": hit.entity.get("chunk_index") or 0,
            "heading": hit.entity.get("heading") or "",
            "text": hit.entity.get("text") or "",
            "source": "milvus",
        }
        for hit in results[0]
    ]


async def retrieve_property_chunks(
    paper_ids: list[str],
    property_name: str,
    limit_per_query: int = 40,
) -> list[dict]:
    chunks: list[dict] = []
    for query in PROPERTY_QUERIES[property_name]:
        try:
            chunks.extend(_es_candidates(paper_ids, query, limit_per_query))
        except Exception:
            pass
        try:
            chunks.extend(await _milvus_candidates(paper_ids, query, limit_per_query))
        except Exception:
            pass
    try:
        chunks.extend(_es_phrase_candidates(paper_ids, property_name, max(limit_per_query * 3, 120)))
    except Exception:
        pass

    deduped = {}
    for chunk in chunks:
        key = f"{chunk['paper_id']}_{chunk['chunk_index']}"
        deduped[key] = chunk
    return list(deduped.values())


def _dedupe_records(records: list[dict]) -> list[dict]:
    deduped = {}
    for record in records:
        key = (
            record.get("paper_id"),
            record.get("property_name"),
            record.get("material_name"),
            record.get("value"),
            record.get("value_max"),
            record.get("source_chunk_id"),
        )
        if key not in deduped or record.get("confidence", 0) > deduped[key].get("confidence", 0):
            deduped[key] = record
    return list(deduped.values())


async def mine_solid_electrolyte_properties(replace: bool = True, limit_per_query: int = 40) -> dict:
    paper_ids = await solid_state_paper_ids()
    if not paper_ids:
        return {"paper_count": 0, "record_count": 0}

    records = []
    for property_name in PROPERTY_QUERIES:
        chunks = await retrieve_property_chunks(paper_ids, property_name, limit_per_query)
        for chunk in chunks:
            for record in extract_property_candidates(
                paper_id=chunk["paper_id"],
                text=chunk["text"],
                heading=chunk.get("heading", ""),
                chunk_index=chunk.get("chunk_index", 0),
            ):
                if record["property_name"] == property_name:
                    records.append(record)

    records = _dedupe_records(records)

    async for db in get_db():
        if replace:
            await db.execute(
                delete(SolidElectrolyteProperty).where(SolidElectrolyteProperty.paper_id.in_(paper_ids))
            )
        for record in records:
            db.add(SolidElectrolyteProperty(**record))
        await db.commit()
        break

    return {"paper_count": len(paper_ids), "record_count": len(records)}
