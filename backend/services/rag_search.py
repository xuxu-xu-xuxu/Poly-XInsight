from backend.services.embedding import embed_single, rerank
from backend.services.ingestion import init_milvus, init_es, COLLECTION_NAME
from collections import defaultdict

RECALL_K = 30
RERANK_K = 20
ENABLE_RERANK = False

async def hybrid_search(query: str, top_k: int = RERANK_K, scope_paper_ids: list[str] | None = None) -> list[dict]:
    if scope_paper_ids is not None and len(scope_paper_ids) == 0:
        return []

    query_vec = await embed_single(query)

    col = init_milvus()
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
    milvus_expr = None
    if scope_paper_ids:
        ids_str = ", ".join(f'"{pid}"' for pid in scope_paper_ids)
        milvus_expr = f"paper_id in [{ids_str}]"
    milvus_results = col.search(
        data=[query_vec], anns_field="embedding", param=search_params,
        limit=RECALL_K, output_fields=["paper_id", "text", "heading", "chunk_index"],
        expr=milvus_expr,
    )

    es = init_es()
    es_body: dict = {
        "query": {
            "bool": {
                "must": [{
                    "multi_match": {
                        "query": query,
                        "fields": ["text^2", "heading"],
                        "operator": "or",
                    }
                }],
            }
        },
        "size": RECALL_K,
        "_source": ["paper_id", "chunk_index", "heading", "text"],
    }
    if scope_paper_ids:
        es_body["query"]["bool"]["filter"] = [{"terms": {"paper_id": scope_paper_ids}}]
    es_results = es.search(index="paper_chunks", body=es_body)

    rrf_scores = defaultdict(float)
    docs = {}
    k = 60
    for rank, hits in enumerate(milvus_results[0]):
        doc_id = f"{hits.entity.get('paper_id')}_{hits.entity.get('chunk_index')}"
        rrf_scores[doc_id] += 1 / (k + rank + 1)
        docs[doc_id] = {
            "paper_id": hits.entity.get("paper_id"),
            "text": hits.entity.get("text"),
            "heading": hits.entity.get("heading"),
            "source": "milvus",
        }
    for rank, hit in enumerate(es_results["hits"]["hits"]):
        doc_id = f"{hit['_source']['paper_id']}_{hit['_source'].get('chunk_index', 'es')}"
        rrf_scores[doc_id] += 1 / (k + rank + 1)
        docs[doc_id] = {
            "paper_id": hit["_source"]["paper_id"],
            "text": hit["_source"].get("text", ""),
            "heading": hit["_source"].get("heading", ""),
            "chunk_index": hit["_source"].get("chunk_index"),
            "source": "es",
        }

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    candidates = [docs[doc_id] for doc_id, _ in ranked[:RECALL_K]]

    # Rerank with BGE-M3 (fallback to original order if rerank fails)
    if ENABLE_RERANK and len(candidates) > top_k:
        try:
            doc_texts = [d["text"] for d in candidates]
            ranked_indices = await rerank(query, doc_texts, top_k=top_k)
            candidates = [candidates[r["index"]] for r in ranked_indices]
        except Exception:
            pass  # fall back to RRF order

    return candidates[:top_k]
