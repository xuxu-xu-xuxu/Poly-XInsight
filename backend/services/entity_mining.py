import re
from collections.abc import Iterable

from sqlalchemy import delete, select

from backend.models.database import Entity, Paper, PaperDomainAssignment, get_db
from backend.services.ingestion import init_es

ENTITY_SOURCE = "entity_mining"

# Common filler names in advanced packaging thermal materials
FILLER_PATTERNS = [
    "BN", "h-BN", "hBN", "boron nitride",
    "AlN", "aluminum nitride",
    "Al2O3", "alumina", "aluminium oxide",
    "SiC", "silicon carbide",
    "SiO2", "silica", "fused silica",
    "graphene", "GO", "rGO", "graphene oxide",
    "CNT", "CNTs", "MWCNT", "carbon nanotube",
    "diamond", "nanodiamond",
    "graphite", "expanded graphite",
    "Ag", "silver",
    "Cu", "copper",
    "ZnO", "zinc oxide",
]

# Common matrix names in advanced packaging
MATRIX_PATTERNS = [
    "epoxy", "epoxy resin", "DGEBA",
    "silicone", "PDMS",
    "polyimide", "PI",
    "BMI", "bismaleimide",
    "cyanate ester",
    "polyurethane", "PU",
    "acrylic",
    "PEEK",
]

MATERIAL_FAMILIES = {
    "TIM1 / thermal interface material": [
        "TIM1", "TIM", "thermal interface material", "热界面材料",
        "导热界面材料", "芯片热界面材料", "散热界面材料",
    ],
    "TIM2": [
        "TIM2", "thermal interface material 2",
    ],
    "die attach adhesive / DAF": [
        "die attach adhesive", "die attach material", "die attach film", "DAF",
        "chip attach adhesive", "芯片粘接材料", "裸片粘接材料", "芯片贴装胶",
        "芯片固定胶", "封装粘接材料",
    ],
    "underfill": [
        "underfill", "capillary underfill", "no-flow underfill",
        "底部填充", "底部填充材料", "毛细底部填充",
    ],
    "mold compound / EMC": [
        "mold compound", "EMC", "epoxy mold compound",
        "encapsulation compound", "封装模塑料", "塑封材料",
    ],
}

PROPERTIES = {
    "thermal conductivity": [
        "thermal conductivity", "导热系数", "导热率", "thermal conductive",
    ],
    "interfacial thermal resistance": [
        "interfacial thermal resistance", "thermal resistance", "界面热阻",
        "thermal interface resistance",
    ],
    "CTE": [
        "CTE", "coefficient of thermal expansion", "thermal expansion coefficient",
        "热膨胀系数",
    ],
    "elastic modulus": [
        "elastic modulus", "storage modulus", "Young's modulus",
        "弹性模量", "储能模量", "杨氏模量",
    ],
    "viscosity": [
        "viscosity", "黏度", "粘度", "complex viscosity",
    ],
    "tensile strength": [
        "tensile strength", "拉伸强度",
    ],
    "warpage": [
        "warpage", "翘曲", "warping",
    ],
    "glass transition temperature": [
        "Tg", "glass transition temperature", "玻璃化转变温度",
    ],
    "thermal diffusivity": [
        "thermal diffusivity", "热扩散系数",
    ],
}

METHODS = {
    "DMA": [
        "DMA", "dynamic mechanical analysis",
    ],
    "TMA": [
        "TMA", "thermomechanical analysis",
    ],
    "laser flash": [
        "laser flash", "LFA", "laser flash analysis",
    ],
    "SEM": [
        "SEM", "scanning electron microscopy",
    ],
    "FEA": [
        "FEA", "finite element analysis", "有限元",
    ],
    "DSC": [
        "DSC", "differential scanning calorimetry",
    ],
    "TGA": [
        "TGA", "thermogravimetric analysis",
    ],
    "rheometer": [
        "rheometer", "流变仪",
    ],
    "thermal cycling": [
        "thermal cycling", "thermal shock", "热循环", "thermal cycle test",
    ],
    "shadow moiré / DIC": [
        "shadow moiré", "digital image correlation", "投影云纹", "数字图像相关", "DIC",
    ],
    "universal testing machine": [
        "UTM", "universal testing machine", "万能试验机",
    ],
}


def _build_filler_re() -> re.Pattern:
    escaped = [re.escape(name) for name in sorted(FILLER_PATTERNS, key=len, reverse=True)]
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)


def _build_matrix_re() -> re.Pattern:
    escaped = [re.escape(name) for name in sorted(MATRIX_PATTERNS, key=len, reverse=True)]
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)


def _extract_filler_entities(
    paper_id: str,
    text: str,
    heading: str,
    chunk_index: int,
) -> list[dict]:
    records = []
    seen: set[str] = set()
    filler_re = _build_filler_re()
    for match in filler_re.finditer(text or ""):
        label = match.group(0).strip()
        if label.lower() in seen:
            continue
        seen.add(label.lower())
        records.append(_record(paper_id, label, "material", text, match.start(), heading, chunk_index))
    return records


def _extract_matrix_entities(
    paper_id: str,
    text: str,
    heading: str,
    chunk_index: int,
) -> list[dict]:
    records = []
    seen: set[str] = set()
    matrix_re = _build_matrix_re()
    for match in matrix_re.finditer(text or ""):
        label = match.group(0).strip()
        if label.lower() in seen:
            continue
        seen.add(label.lower())
        records.append(_record(paper_id, label, "material", text, match.start(), heading, chunk_index))
    return records


def _snippet(text: str, position: int, width: int = 220) -> str:
    start = max(0, position - width // 2)
    end = min(len(text), position + width // 2)
    return re.sub(r"\s+", " ", text[start:end]).strip()[:256]


def _phrase_pattern(variant: str) -> re.Pattern:
    escaped = re.escape(variant).replace(r"\ ", r"\s+")
    if re.fullmatch(r"[A-Za-z0-9+.-]+", variant):
        return re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def _record(
    paper_id: str,
    label: str,
    kind: str,
    text: str,
    position: int,
    heading: str,
    chunk_index: int,
    extra: dict | None = None,
) -> dict:
    attributes = {
        "kind": kind,
        "source": ENTITY_SOURCE,
        "source_chunk_id": f"{paper_id}_{chunk_index}",
        "heading": heading or "",
    }
    if extra:
        attributes.update(extra)
    return {
        "paper_id": paper_id,
        "entity_type": label,
        "attributes": attributes,
        "source_span": _snippet(text, position),
    }


def _extract_phrase_entities(
    paper_id: str,
    text: str,
    heading: str,
    chunk_index: int,
    kind: str,
    vocabulary: dict[str, list[str]],
) -> list[dict]:
    records = []
    for label, variants in vocabulary.items():
        for variant in variants:
            match = _phrase_pattern(variant).search(text)
            if not match:
                continue
            records.append(_record(paper_id, label, kind, text, match.start(), heading, chunk_index))
            break
    return records


def extract_chunk_entities(
    paper_id: str,
    text: str,
    heading: str = "",
    chunk_index: int = 0,
) -> list[dict]:
    records = []
    text = text or ""

    records.extend(_extract_filler_entities(paper_id, text, heading, chunk_index))
    records.extend(_extract_matrix_entities(paper_id, text, heading, chunk_index))
    records.extend(_extract_phrase_entities(paper_id, text, heading, chunk_index, "material_family", MATERIAL_FAMILIES))
    records.extend(_extract_phrase_entities(paper_id, text, heading, chunk_index, "property", PROPERTIES))
    records.extend(_extract_phrase_entities(paper_id, text, heading, chunk_index, "method", METHODS))

    return unique_entity_records(records)


def unique_entity_records(records: Iterable[dict]) -> list[dict]:
    deduped = {}
    for record in records:
        kind = (record.get("attributes") or {}).get("kind", "")
        key = (record.get("paper_id"), record.get("entity_type"), kind)
        if key not in deduped:
            deduped[key] = record
    return list(deduped.values())


async def _paper_ids(domain_id: str | None = None, limit: int | None = None) -> list[str]:
    async for db in get_db():
        query = select(Paper.id).where(Paper.status == "ingested").order_by(Paper.created_at.desc())
        if domain_id:
            query = (
                query
                .join(PaperDomainAssignment, PaperDomainAssignment.paper_id == Paper.id)
                .where(PaperDomainAssignment.domain_id == domain_id)
            )
        if limit:
            query = query.limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    return []


def _fetch_chunks(paper_ids: list[str], chunk_limit: int) -> list[dict]:
    if not paper_ids:
        return []
    es = init_es()
    response = es.search(
        index="paper_chunks",
        body={
            "query": {"terms": {"paper_id": paper_ids}},
            "size": chunk_limit,
            "_source": ["paper_id", "chunk_index", "heading", "text"],
            "sort": [{"paper_id": "asc"}, {"chunk_index": "asc"}],
        },
    )
    return [
        {
            "paper_id": hit["_source"]["paper_id"],
            "chunk_index": hit["_source"].get("chunk_index", 0),
            "heading": hit["_source"].get("heading", ""),
            "text": hit["_source"].get("text", ""),
        }
        for hit in response["hits"]["hits"]
    ]


async def mine_entities(
    domain_id: str | None = None,
    replace: bool = True,
    paper_limit: int | None = None,
    chunk_limit: int = 10000,
) -> dict:
    paper_ids = await _paper_ids(domain_id=domain_id, limit=paper_limit)
    chunks = _fetch_chunks(paper_ids, chunk_limit)
    records = []
    for chunk in chunks:
        records.extend(extract_chunk_entities(
            paper_id=chunk["paper_id"],
            text=chunk["text"],
            heading=chunk.get("heading", ""),
            chunk_index=chunk.get("chunk_index", 0),
        ))
    records = unique_entity_records(records)

    async for db in get_db():
        if replace and paper_ids:
            await db.execute(
                delete(Entity)
                .where(Entity.paper_id.in_(paper_ids))
                .where(Entity.attributes["source"].as_string() == ENTITY_SOURCE)
            )
        for record in records:
            db.add(Entity(**record))
        await db.commit()
        break

    return {
        "paper_count": len(paper_ids),
        "chunk_count": len(chunks),
        "entity_count": len(records),
        "source": ENTITY_SOURCE,
    }
