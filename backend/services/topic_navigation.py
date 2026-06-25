from __future__ import annotations

import re
from collections import Counter, defaultdict
from hashlib import md5
from typing import Iterable

from sqlalchemy import select

from backend.models.database import (
    Entity,
    LibraryDomain,
    Paper,
    PaperDomainAssignment,
    PaperTag,
    ThermalConductiveProperty,
    get_db,
)

TOPIC_PREFIX_RE = re.compile(r"^\[[^\]]+\]\s*")
SLUG_TOKEN_RE = re.compile(r"[^a-z0-9]+")

# ── Advanced packaging materials: common problem signals ───────────────

PROBLEM_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("interfacial thermal resistance", (
        "interfacial thermal resistance", "interface thermal resistance",
        "thermal interface resistance", "界面热阻", "interface resistance",
        "Kapitza resistance", "thermal boundary resistance",
    )),
    ("pump-out", (
        "pump-out", "pump out", "泵出效应", "泵出",
    )),
    ("delamination", (
        "delamination", "interfacial delamination",
        "界面剥离", "界面分离", "adhesion failure",
    )),
    ("warpage / CTE mismatch", (
        "warpage", "翘曲", "CTE mismatch", "thermal mismatch",
        "thermal expansion mismatch", "热膨胀失配",
    )),
    ("thermal reliability", (
        "thermal cycling", "thermal shock", "热循环", "热冲击",
        "moisture sensitivity", "humidity aging", "湿热老化",
        "reliability test", "JEDEC", "temperature cycling",
    )),
]

SIGNAL_ORDER = ("materials", "methods", "problems", "properties")
SIGNAL_NODE_TYPE = {
    "materials": "material",
    "methods": "method",
    "problems": "problem",
    "properties": "property",
}

DOMAIN_LABEL_FALLBACKS = {
    "solid-state": "Solid-state",
    "electrocatalysis": "Electrocatalysis",
    "writing-tips": "Writing",
    "thermal-polymer": "Thermal Polymer",
    "unclassified": "Unclassified",
}


def _normalize_whitespace(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _slugify(value: str) -> str:
    lowered = value.lower().strip()
    ascii_only = lowered.encode("ascii", "ignore").decode("ascii")
    slug = SLUG_TOKEN_RE.sub("-", ascii_only).strip("-")
    if slug:
        return slug
    return f"item-{md5(lowered.encode('utf-8')).hexdigest()[:10]}"


def _strip_topic_prefix(value: str | None) -> str:
    clean = _normalize_whitespace(value)
    return TOPIC_PREFIX_RE.sub("", clean).strip() or "Unclustered literature"


def _clean_signal_label(value: str | None) -> str:
    clean = _normalize_whitespace((value or "").replace("_", " "))
    clean = clean.strip(".,;:()[]{}")
    if clean.lower() in {"unknown", "n/a", "none"}:
        return ""
    return clean


def _display_domain_name(domain_id: str, domain_name: str | None) -> str:
    clean = _normalize_whitespace(domain_name)
    if not clean:
        return DOMAIN_LABEL_FALLBACKS.get(domain_id, domain_id)
    if "å" in clean or "�" in clean:
        return DOMAIN_LABEL_FALLBACKS.get(domain_id, domain_id)
    return clean


def infer_problem_signals(text: str | None) -> list[str]:
    haystack = (text or "").lower()
    found: list[str] = []
    for label, patterns in PROBLEM_PATTERNS:
        if any(pattern in haystack for pattern in patterns):
            found.append(label)
    return found


def _top_counts(values: Iterable[str], limit: int = 5) -> list[dict]:
    counts = Counter(value for value in values if value)
    return [
        {"label": label, "count": count}
        for label, count in counts.most_common(limit)
    ]


def build_topic_cards(
    papers: list[dict],
    max_topics: int = 8,
    papers_per_topic: int = 4,
    signals_per_type: int = 5,
) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for paper in papers:
        label = _strip_topic_prefix(paper.get("topic_label"))
        grouped[label].append(paper)

    cards: list[dict] = []
    for label, group in grouped.items():
        sorted_group = sorted(
            group,
            key=lambda item: (
                -len(sum((item.get("signals", {}).get(kind, []) for kind in SIGNAL_ORDER), [])),
                -(item.get("year") or 0),
                item.get("title") or "",
            ),
        )
        highlights = {}
        for kind in SIGNAL_ORDER:
            highlights[kind] = _top_counts(
                (
                    signal
                    for paper in group
                    for signal in paper.get("signals", {}).get(kind, [])
                ),
                signals_per_type,
            )
        cards.append(
            {
                "id": f"topic:{_slugify(label)}",
                "label": label,
                "domain_id": sorted_group[0].get("domain_id"),
                "is_fallback_topic": all(bool(paper.get("is_fallback_topic")) for paper in group),
                "paper_count": len(group),
                "papers": [
                    {
                        "id": paper["id"],
                        "title": paper.get("title") or "",
                        "year": paper.get("year"),
                        "journal": paper.get("journal"),
                    }
                    for paper in sorted_group[:papers_per_topic]
                ],
                "highlights": highlights,
            }
        )

    cards.sort(key=lambda item: (-item["paper_count"], item["label"].lower()))
    return cards[:max_topics]


def build_topic_graph(
    cards: list[dict],
    include_domains: bool = True,
) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for card in cards:
        topic_id = card["id"]
        domain_id = card.get("domain_id") or "unclassified"

        nodes.setdefault(
            topic_id,
            {
                "id": topic_id,
                "label": card["label"],
                "type": "topic",
                "size": min(24, 10 + card["paper_count"] * 1.4),
                "domain_id": domain_id,
                "meta": {"paper_count": card["paper_count"]},
            },
        )

        if include_domains:
            domain_node_id = f"domain:{domain_id}"
            nodes.setdefault(
                domain_node_id,
                {
                    "id": domain_node_id,
                    "label": card.get("domain_name") or domain_id,
                    "type": "domain",
                    "size": 18,
                    "domain_id": domain_id,
                    "meta": {},
                },
            )
            edges.append(
                {
                    "id": f"{domain_node_id}->{topic_id}",
                    "source": domain_node_id,
                    "target": topic_id,
                    "type": "domain_topic",
                    "weight": max(1.0, card["paper_count"]),
                }
            )

        for paper in card.get("papers", []):
            paper_node_id = f"paper:{paper['id']}"
            nodes.setdefault(
                paper_node_id,
                {
                    "id": paper_node_id,
                    "label": paper["title"],
                    "type": "paper",
                    "size": 8,
                    "paper_id": paper["id"],
                    "domain_id": domain_id,
                    "meta": {"year": paper.get("year"), "journal": paper.get("journal")},
                },
            )
            edges.append(
                {
                    "id": f"{topic_id}->{paper_node_id}",
                    "source": topic_id,
                    "target": paper_node_id,
                    "type": "topic_paper",
                    "weight": 1.6,
                }
            )

        for kind in SIGNAL_ORDER:
            for signal in card.get("highlights", {}).get(kind, []):
                label = signal["label"]
                node_type = SIGNAL_NODE_TYPE[kind]
                node_id = f"{node_type}:{_slugify(label)}"
                nodes.setdefault(
                    node_id,
                    {
                        "id": node_id,
                        "label": label,
                        "type": node_type,
                        "size": min(18, 6 + signal["count"] * 1.1),
                        "domain_id": domain_id,
                        "meta": {"count": signal["count"], "kind": kind},
                    },
                )
                edges.append(
                    {
                        "id": f"{topic_id}->{node_id}",
                        "source": topic_id,
                        "target": node_id,
                        "type": "topic_signal",
                        "weight": max(1.0, signal["count"]),
                    }
                )

    return {"nodes": list(nodes.values()), "edges": edges}


def _extract_entity_signals(entity_rows: list[Entity]) -> dict[str, set[str]]:
    signals: dict[str, set[str]] = defaultdict(set)
    for row in entity_rows:
        kind = _normalize_whitespace(str((row.attributes or {}).get("kind", ""))).lower()
        label = _clean_signal_label(row.entity_type)
        if not label:
            continue
        if kind in {"material", "material_family"}:
            signals["materials"].add(label)
        elif kind == "method":
            signals["methods"].add(label)
        elif kind == "property":
            signals["properties"].add(label)
    return signals


def _merge_signal_map(base: dict[str, set[str]], extra: dict[str, Iterable[str]]) -> dict[str, set[str]]:
    for key, values in extra.items():
        base.setdefault(key, set()).update(value for value in values if value)
    return base


async def load_topic_cards(
    domain_id: str | None = None,
    max_topics: int = 8,
    papers_per_topic: int = 4,
) -> dict:
    async for db in get_db():
        domain_result = await db.execute(select(LibraryDomain))
        domains = {
            domain.id: _display_domain_name(domain.id, domain.name)
            for domain in domain_result.scalars().all()
        }

        paper_query = (
            select(Paper, PaperDomainAssignment.domain_id)
            .join(PaperDomainAssignment, PaperDomainAssignment.paper_id == Paper.id, isouter=True)
            .where(Paper.status == "ingested")
            .order_by(Paper.created_at.desc())
        )
        if domain_id:
            paper_query = paper_query.where(PaperDomainAssignment.domain_id == domain_id)
        paper_rows = (await db.execute(paper_query)).all()
        papers = [paper for paper, _domain in paper_rows]
        paper_ids = [paper.id for paper in papers]
        domain_by_paper = {paper.id: assigned_domain for paper, assigned_domain in paper_rows}

        tag_rows = []
        entity_rows = []
        thermal_property_rows = []
        if paper_ids:
            tag_rows = (
                await db.execute(
                    select(PaperTag.paper_id, PaperTag.tag)
                    .where(PaperTag.paper_id.in_(paper_ids))
                    .where(PaperTag.source == "cluster")
                )
            ).all()
            entity_rows = (
                await db.execute(select(Entity).where(Entity.paper_id.in_(paper_ids)))
            ).scalars().all()
            thermal_property_rows = (
                await db.execute(
                    select(ThermalConductiveProperty).where(
                        ThermalConductiveProperty.paper_id.in_(paper_ids)
                    )
                )
            ).scalars().all()
        break

    cluster_by_paper = {paper_id: tag for paper_id, tag in tag_rows}
    entities_by_paper: dict[str, list[Entity]] = defaultdict(list)
    for row in entity_rows:
        entities_by_paper[row.paper_id].append(row)

    thermal_by_paper: dict[str, list[ThermalConductiveProperty]] = defaultdict(list)
    for row in thermal_property_rows:
        thermal_by_paper[row.paper_id].append(row)

    paper_payloads: list[dict] = []
    for paper in papers:
        signal_map = _extract_entity_signals(entities_by_paper.get(paper.id, []))

        # Merge signals from ThermalConductiveProperty table
        signal_map = _merge_signal_map(
            signal_map,
            {
                "materials": [
                    _clean_signal_label(prop.filler_name)
                    for prop in thermal_by_paper.get(paper.id, [])
                ] + [
                    _clean_signal_label(prop.matrix_name)
                    for prop in thermal_by_paper.get(paper.id, [])
                ],
                "methods": [
                    _clean_signal_label(prop.method)
                    for prop in thermal_by_paper.get(paper.id, [])
                ],
                "properties": [
                    _clean_signal_label(prop.property_name)
                    for prop in thermal_by_paper.get(paper.id, [])
                ],
            },
        )
        signal_map["problems"].update(
            infer_problem_signals(
                "\n".join(
                    part
                    for part in [
                        paper.title,
                        paper.abstract,
                        (paper.full_text or "")[:5000],
                    ]
                    if part
                )
            )
        )

        topic_label = _strip_topic_prefix(cluster_by_paper.get(paper.id))
        is_fallback_topic = False
        if topic_label == "Unclustered literature":
            domain_label = domains.get(domain_by_paper.get(paper.id) or "", "")
            topic_label = f"{domain_label or 'General'} literature"
            is_fallback_topic = True

        paper_payloads.append(
            {
                "id": paper.id,
                "title": paper.title,
                "year": paper.year,
                "journal": paper.journal,
                "domain_id": domain_by_paper.get(paper.id) or "unclassified",
                "topic_label": topic_label,
                "is_fallback_topic": is_fallback_topic,
                "signals": {
                    key: sorted(values)
                    for key, values in signal_map.items()
                },
            }
        )

    cards = build_topic_cards(
        paper_payloads,
        max_topics=max_topics,
        papers_per_topic=papers_per_topic,
    )
    for card in cards:
        card["domain_name"] = domains.get(card["domain_id"], card["domain_id"])

    return {
        "items": cards,
        "stats": {
            "topic_count": len(cards),
            "paper_count": len(paper_payloads),
            "domain_count": len({card["domain_id"] for card in cards}),
            "fallback_topic_count": sum(1 for card in cards if card.get("is_fallback_topic")),
        },
    }


async def load_topic_graph(
    domain_id: str | None = None,
    max_topics: int = 8,
    papers_per_topic: int = 4,
) -> dict:
    payload = await load_topic_cards(
        domain_id=domain_id,
        max_topics=max_topics,
        papers_per_topic=papers_per_topic,
    )
    graph = build_topic_graph(payload["items"], include_domains=not domain_id)
    graph["stats"] = payload["stats"]
    return graph
