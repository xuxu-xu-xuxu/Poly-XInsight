from sqlalchemy import delete, select

from backend.models.database import (
    Paper,
    PaperDomainAssignment,
    ThermalConductiveProperty,
    get_db,
)
from backend.services.embedding import embed_single
from backend.services.ingestion import init_es, init_milvus
from backend.services.thermal_conductive_properties.extractor import extract_thermal_conductive_candidates

THERMAL_POLYMER_DOMAIN_ID = "thermal-polymer"

PROPERTY_QUERIES = {
    "thermal": [
        "thermal conductivity polymer composite filler W/mK",
        "thermal resistance interfacial thermal management TIM",
        "thermal diffusivity CTE polymer composite heat dissipation",
        "thermal interface material heat conduction network percolation",
    ],
    "rheological": [
        "rheological viscosity storage modulus polymer composite filler",
        "G' G\" complex viscosity shear thinning polymer melt",
        "dynamic mechanical analysis DMA filler network viscoelastic",
        "tan delta loss factor polymer composite rheology",
    ],
    "mechanical": [
        "tensile strength Young's modulus polymer composite filler mechanical",
        "flexural impact strength hardness polymer nanocomposite",
        "elongation at break toughness polymer composite mechanical properties",
        "compressive shear strength polymer composite filler reinforcement",
    ],
    "composition": [
        "BN AlN filler content wt% polymer matrix composite",
        "filler loading volume fraction thermal conductive polymer",
        "surface treatment silane coupling agent filler modification",
        "particle size distribution filler dispersion polymer composite",
    ],
}

PROPERTY_PHRASES = {
    "thermal": [
        "W/mK", "W/(m·K)", "W m-1 K-1", "thermal conductivity",
        "thermal resistance", "thermal diffusivity", "CTE",
        "heat dissipation", "thermal interface",
    ],
    "rheological": [
        "storage modulus", "loss modulus", "complex viscosity",
        "shear viscosity", "tan delta", "yield stress",
        "viscoelastic", "rheological", "G'", "G\"",
    ],
    "mechanical": [
        "tensile strength", "Young's modulus", "elongation at break",
        "flexural strength", "flexural modulus", "impact strength",
        "compressive strength", "shear strength", "hardness",
    ],
    "composition": [
        "wt%", "vol%", "filler content", "filler loading",
        "weight fraction", "volume fraction", "surface treatment",
        "particle size", "filler dispersion",
    ],
}


async def thermal_polymer_paper_ids() -> list[str]:
    async for db in get_db():
        result = await db.execute(
            select(Paper.id)
            .join(PaperDomainAssignment, PaperDomainAssignment.paper_id == Paper.id)
            .where(PaperDomainAssignment.domain_id == THERMAL_POLYMER_DOMAIN_ID)
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


def _es_phrase_candidates(paper_ids: list[str], property_key: str, size: int) -> list[dict]:
    es = init_es()
    should = [
        {"match_phrase": {"text": phrase}}
        for phrase in PROPERTY_PHRASES[property_key]
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
    ids_str = ", ".join(f'"{pid}"' for pid in paper_ids)
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


async def _retrieve_property_chunks(
    paper_ids: list[str],
    property_key: str,
    limit_per_query: int = 40,
) -> list[dict]:
    chunks: list[dict] = []
    for query in PROPERTY_QUERIES[property_key]:
        try:
            chunks.extend(_es_candidates(paper_ids, query, limit_per_query))
        except Exception:
            pass
        try:
            chunks.extend(await _milvus_candidates(paper_ids, query, limit_per_query))
        except Exception:
            pass
    try:
        chunks.extend(_es_phrase_candidates(paper_ids, property_key, max(limit_per_query * 3, 120)))
    except Exception:
        pass

    deduped: dict[str, dict] = {}
    for chunk in chunks:
        key = f"{chunk['paper_id']}_{chunk['chunk_index']}"
        deduped[key] = chunk
    return list(deduped.values())


def _dedupe_records(records: list[dict]) -> list[dict]:
    deduped: dict[tuple, dict] = {}
    for record in records:
        key = (
            record.get("paper_id"),
            record.get("property_category"),
            record.get("property_name"),
            record.get("filler_name"),
            record.get("matrix_name"),
            record.get("value"),
            record.get("value_max"),
            record.get("source_chunk_id"),
        )
        if key not in deduped or record.get("confidence", 0) > deduped[key].get("confidence", 0):
            deduped[key] = record
    return list(deduped.values())


# Simple in-memory guard to prevent concurrent mining runs
_mining_lock = False


async def mine_thermal_conductive_properties(replace: bool = True, limit_per_query: int = 40) -> dict:
    global _mining_lock
    if _mining_lock:
        return {"paper_count": 0, "record_count": 0, "skipped": True, "reason": "mining already in progress"}
    _mining_lock = True

    try:
        paper_ids = await thermal_polymer_paper_ids()
        if not paper_ids:
            return {"paper_count": 0, "record_count": 0}

        records = []
        for property_key in PROPERTY_QUERIES:
            chunks = await _retrieve_property_chunks(paper_ids, property_key, limit_per_query)
            for chunk in chunks:
                candidates = extract_thermal_conductive_candidates(
                    paper_id=chunk["paper_id"],
                    text=chunk["text"],
                    heading=chunk.get("heading", ""),
                    chunk_index=chunk.get("chunk_index", 0),
                )
                for record in candidates:
                    records.append(record)

        records = _dedupe_records(records)

        async for db in get_db():
            if replace:
                await db.execute(
                    delete(ThermalConductiveProperty).where(
                        ThermalConductiveProperty.paper_id.in_(paper_ids)
                    )
                )
                for record in records:
                    db.add(ThermalConductiveProperty(**record))
            else:
                # Dedup against existing records in DB
                for record in records:
                    existing = await db.execute(
                        select(ThermalConductiveProperty.id).where(
                            ThermalConductiveProperty.paper_id == record["paper_id"],
                            ThermalConductiveProperty.property_category == record["property_category"],
                            ThermalConductiveProperty.property_name == record["property_name"],
                            ThermalConductiveProperty.filler_name == record["filler_name"],
                            ThermalConductiveProperty.matrix_name == record.get("matrix_name"),
                            ThermalConductiveProperty.value == record.get("value"),
                        ).limit(1)
                    )
                    if existing.scalar() is None:
                        db.add(ThermalConductiveProperty(**record))
            await db.commit()
            break

        return {"paper_count": len(paper_ids), "record_count": len(records)}
    finally:
        _mining_lock = False
