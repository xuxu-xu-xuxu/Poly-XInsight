from backend.services.rag_service import QUERY_REWRITE_PROMPT, RAG_SYSTEM_PROMPT


def test_rewrite_prompt_contains_query_placeholder():
    assert "{query}" in QUERY_REWRITE_PROMPT


def test_system_prompt_requires_citations():
    assert "来源" in RAG_SYSTEM_PROMPT
    assert "未找到相关信息" in RAG_SYSTEM_PROMPT
    assert "禁止编造" in RAG_SYSTEM_PROMPT
