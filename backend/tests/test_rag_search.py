from collections import defaultdict
import asyncio

from backend.services import rag_search
from backend.models.schemas import ChatRequest

def test_rrf_same_doc_gets_higher_score():
    rrf = defaultdict(float)
    k = 60
    for rank in range(10):
        rrf["doc1"] += 1 / (k + rank + 1)
    for rank in range(10):
        rrf["doc1"] += 1 / (k + rank + 1)
    for rank in range(10):
        rrf["doc2"] += 1 / (k + rank + 1)
    ranked = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
    assert ranked[0][0] == "doc1"
    assert ranked[1][0] == "doc2"


def test_chat_request_accepts_domain_scope():
    request = ChatRequest(query="compare electrolytes", scope_domain_id="solid-state")

    assert request.scope_domain_id == "solid-state"


def test_hybrid_search_empty_scope_returns_no_docs(monkeypatch):
    async def fail_embed(_query: str):
        raise AssertionError("empty scoped search should not embed or query indexes")

    monkeypatch.setattr(rag_search, "embed_single", fail_embed)

    assert asyncio.run(rag_search.hybrid_search("query", scope_paper_ids=[])) == []
