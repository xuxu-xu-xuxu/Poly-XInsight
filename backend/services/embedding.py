import asyncio
import httpx
from backend.config import get_settings


async def _embed_batch(client: httpx.AsyncClient, batch: list[str], return_sparse: bool, url: str) -> tuple[list, list]:
    resp = await client.post(
        url,
        json={"sentences": batch, "return_sparse": return_sparse}
    )
    resp.raise_for_status()
    result = resp.json()
    return result["dense_embeddings"], result.get("sparse_embeddings", [])


async def embed_sentences(sentences: list[str], return_sparse: bool = False, concurrency: int = 3) -> dict:
    """
    Embed sentences with async concurrent batch calls.
    Splits into batches and sends them in parallel, dramatically
    reducing total time when BGE is CPU-bound on large documents.
    """
    if not sentences:
        return {"dense_embeddings": [], "sparse_embeddings": []}

    settings = get_settings()
    batch_size = max(1, settings.embedding_batch_size)
    url = settings.bge_embed_url

    # Build batches
    batches: list[list[str]] = []
    for i in range(0, len(sentences), batch_size):
        batches.append(sentences[i : i + batch_size])

    all_dense = []
    all_sparse = []

    async with httpx.AsyncClient(timeout=300) as client:
        sem = asyncio.Semaphore(concurrency)

        async def bounded_batch(batch):
            async with sem:
                return await _embed_batch(client, batch, return_sparse, url)

        tasks = [bounded_batch(b) for b in batches]
        results = await asyncio.gather(*tasks)

        for dense, sparse in results:
            all_dense.extend(dense)
            if return_sparse:
                all_sparse.extend(sparse)

    return {"dense_embeddings": all_dense, "sparse_embeddings": all_sparse}


async def embed_single(text: str) -> list[float]:
    result = await embed_sentences([text], concurrency=1)
    return result["dense_embeddings"][0]

async def rerank(query: str, documents: list[str], top_k: int = 10) -> list[dict]:
    settings = get_settings()
    url = settings.bge_embed_url.replace("/embed", "/rerank")
    docs = [d[:1024] for d in documents]
    ranked = []
    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(docs), 15):
            batch = docs[i : i + 15]
            resp = await client.post(url, json={"query": query, "documents": batch})
            resp.raise_for_status()
            result = resp.json()
            for item in result["ranked"]:
                item["index"] += i
                ranked.append(item)
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]
