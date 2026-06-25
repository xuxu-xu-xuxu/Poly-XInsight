"""Paper classification service: LLM tagging + vector clustering."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

from backend.llm import get_llm_client
from backend.models.database import Paper, PaperTag, get_db

logger = logging.getLogger(__name__)

TAG_VOCABULARY = {
    "研究领域": ["CO2还原", "固态电解质", "电催化", "电池材料", "表征技术", "计算模拟", "合成制备", "机理研究"],
    "材料类型": ["氧化物", "硫化物", "聚合物", "金属合金", "碳材料", "MOF/COF", "二维材料", "钙钛矿"],
    "方法类型": ["实验研究", "DFT计算", "AIMD模拟", "机器学习", "原位表征", "理论分析"],
}

ALL_TAGS = [tag for group in TAG_VOCABULARY.values() for tag in group]

CLASSIFY_PROMPT = """你是一个材料科学文献分类专家。请根据以下论文内容，从预设标签列表中选择最匹配的 2-5 个标签。

标签列表（只能从以下标签中选择，不要自创标签）：
{tag_list}

论文标题：{title}
论文摘要：{abstract}

输出严格的 JSON 数组格式（只输出 JSON，不要其他文字）：
["标签1", "标签2", "标签3"]

如果论文内容不足以判断，选择最接近的标签。"""

CLUSTER_NAME_PROMPT = """以下是同一聚类中的论文标题列表。请根据这些标题为该聚类生成一个简洁的中文名称（不超过10个字），描述该组论文的共同研究主题。

只返回名称本身，不要加任何解释。

论文标题：
{titles}"""


def _clean_json_response(response: str) -> str:
    response = response.strip()
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = response.find(start_char)
        end = response.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return response[start : end + 1]
    return response


def _parse_tag_response(response: str) -> list[str]:
    cleaned = _clean_json_response(response)
    try:
        tags = json.loads(cleaned)
        if isinstance(tags, list):
            return [tag for tag in tags if isinstance(tag, str) and tag in ALL_TAGS]
    except json.JSONDecodeError:
        matches = re.findall(r'"([^"]+)"', cleaned)
        tags = [match for match in matches if match in ALL_TAGS]
        if tags:
            return tags
    return []


def _normalize_cluster_text(*parts: str | None, max_length: int = 8000) -> str:
    joined = "\n".join(part.strip() for part in parts if part and part.strip())
    return joined[:max_length]


def _build_cluster_documents(rows: list[tuple[str | None, str | None, str | None, str | None]]) -> list[dict]:
    papers: list[dict] = []
    for paper_id, title, abstract, full_text in rows:
        cluster_text = _normalize_cluster_text(
            abstract,
            title,
            (full_text or "")[:4000],
        )
        if not cluster_text:
            continue
        papers.append(
            {
                "id": paper_id,
                "title": title or "Untitled paper",
                "cluster_text": cluster_text,
            }
        )
    return papers


async def classify_single_paper(paper_id: str) -> list[str]:
    async for db in get_db():
        paper = await db.get(Paper, paper_id)
        break
    if not paper:
        logger.warning("Paper %s not found, skipping classification", paper_id)
        return []

    abstract = _normalize_cluster_text(paper.abstract, paper.title, (paper.full_text or "")[:4000])

    prompt = CLASSIFY_PROMPT.format(
        tag_list=", ".join(ALL_TAGS),
        title=paper.title or "",
        abstract=abstract,
    )
    try:
        llm = get_llm_client()
        response = await llm.chat([{"role": "user", "content": prompt}])
        tags = _parse_tag_response(response)
    except Exception as exc:
        logger.error("LLM classification failed for paper %s: %s", paper_id, exc)
        return []

    if not tags:
        logger.info("No valid tags returned for paper %s", paper_id)
        return []

    stored = 0
    async for db in get_db():
        for tag_name in tags:
            try:
                db.add(PaperTag(paper_id=paper_id, tag=tag_name, source="llm"))
                await db.commit()
                stored += 1
            except Exception:
                await db.rollback()
        break

    logger.info("Classified paper %s with tags: %s (%d stored)", paper_id, tags, stored)
    return tags


async def classify_all_papers() -> dict:
    async for db in get_db():
        subquery = select(PaperTag.paper_id).where(PaperTag.source == "llm")
        result = await db.execute(
            select(Paper.id, Paper.title)
            .where(Paper.status == "ingested")
            .where(Paper.id.not_in(subquery))
        )
        papers = [{"id": row[0], "title": row[1]} for row in result.fetchall()]
        break

    if not papers:
        return {"total": 0, "classified": 0, "skipped": 0}

    classified = 0
    errors = []
    total = len(papers)

    for index, paper in enumerate(papers, start=1):
        try:
            tags = await classify_single_paper(paper["id"])
            if tags:
                classified += 1
            logger.info("[%d/%d] Classified: %s", index, total, paper["title"][:60])
        except Exception as exc:
            errors.append({"paper_id": paper["id"], "title": paper["title"], "error": str(exc)})
            logger.error("[%d/%d] Failed: %s - %s", index, total, paper["title"][:60], exc)
        await asyncio.sleep(0.5)

    return {"total": total, "classified": classified, "errors": errors}


async def cluster_papers(n_clusters: int = 8) -> dict:
    from backend.services.embedding import embed_single

    async for db in get_db():
        result = await db.execute(
            select(Paper.id, Paper.title, Paper.abstract, Paper.full_text)
            .where(Paper.status == "ingested")
        )
        rows = result.fetchall()
        break

    papers = _build_cluster_documents(rows)
    if len(papers) < 2:
        return {"clusters": [], "error": "Not enough papers with clusterable text"}

    logger.info("Embedding %d paper documents for clustering...", len(papers))
    vectors = []
    valid_papers = []
    for paper in papers:
        try:
            vec = await embed_single(paper["cluster_text"])
            vectors.append(vec)
            valid_papers.append(paper)
        except Exception as exc:
            logger.warning("Embedding failed for %s: %s", paper["id"], exc)

    if len(valid_papers) < 2:
        return {"clusters": [], "error": "Not enough successful embeddings"}

    from sklearn.cluster import KMeans
    import numpy as np

    x = np.array(vectors)
    actual_k = min(n_clusters, len(valid_papers))
    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(x)

    clusters: dict[int, list[dict]] = {}
    for index, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(valid_papers[index])

    cluster_results = []
    llm = get_llm_client()
    for label, cluster_papers_list in clusters.items():
        sample_titles = [paper["title"] for paper in cluster_papers_list[:10]]
        prompt = CLUSTER_NAME_PROMPT.format(titles="\n".join(f"- {title}" for title in sample_titles))
        try:
            name = (await llm.chat([{"role": "user", "content": prompt}])).strip()
            name = name.replace('"', "").replace("'", "").replace("\n", "").strip()
        except Exception:
            name = f"聚类 {label + 1}"

        cluster_results.append(
            {
                "name": name,
                "count": len(cluster_papers_list),
                "paper_ids": [paper["id"] for paper in cluster_papers_list],
            }
        )

    async for db in get_db():
        await db.execute(sa_delete(PaperTag).where(PaperTag.source == "cluster"))
        await db.commit()
        break

    for cluster_result in cluster_results:
        tag_name = f"[聚类] {cluster_result['name']}"
        async for db in get_db():
            for paper_id in cluster_result["paper_ids"]:
                db.add(PaperTag(paper_id=paper_id, tag=tag_name, source="cluster"))
            await db.commit()
            break

    logger.info("Clustering complete: %d clusters", len(cluster_results))
    return {"clusters": cluster_results}


async def get_categories() -> list[dict]:
    async for db in get_db():
        result = await db.execute(
            select(PaperTag.tag, func.count(PaperTag.paper_id).label("cnt"))
            .group_by(PaperTag.tag)
            .order_by(func.count(PaperTag.paper_id).desc())
        )
        tag_counts = {row[0]: row[1] for row in result.fetchall()}
        break

    categories = []
    for group_name, group_tags in TAG_VOCABULARY.items():
        for tag_name in group_tags:
            count = tag_counts.get(tag_name, 0)
            if count > 0:
                categories.append({"tag": tag_name, "count": count, "category": group_name})

    for tag_name, count in tag_counts.items():
        if tag_name.startswith("[聚类]"):
            categories.append({"tag": tag_name, "count": count, "category": "聚类结果"})

    return categories
