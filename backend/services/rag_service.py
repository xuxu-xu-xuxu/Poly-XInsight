from backend.llm import get_llm_client

QUERY_REWRITE_PROMPT = """你是一个材料科学文献检索专家。将用户的问题改写为更适合检索的查询。
- 将口语化表达转换为学术术语
- 中文和英文术语都保留（中英双语查询）
- 如果问题涉及缩写，同时保留全称和缩写
- 只输出改写后的查询，不要解释

用户问题: {query}
改写查询:"""

RAG_SYSTEM_PROMPT = """你是一个材料科学文献助手。请根据提供的文献片段回答用户的问题。

必须遵守以下规则：
1. 回答要详细、具体、有深度。不要只给一句话概括，要展开论述
2. 每个事实性陈述后标注来源引用：[文献N]
3. 如果文献片段中找不到相关信息，明确说"当前文献库中未找到该信息"
4. 禁止编造任何文献中不存在的数据或结论
5. 回答末尾不需要列出参考文献，系统会自动追加"""


async def rewrite_query(query: str) -> str:
    llm = get_llm_client()
    prompt = QUERY_REWRITE_PROMPT.format(query=query)
    return await llm.chat([{"role": "user", "content": prompt}])


async def generate_answer_stream(
    query: str,
    conversation_history: list[dict] = None,
    scope_paper_ids: list[str] | None = None,
    scope_domain_id: str | None = None,
):
    from backend.services.rag_search import hybrid_search
    from backend.models.database import get_db, Paper, PaperDomainAssignment
    from sqlalchemy import func, select as sa_select

    yield "🔍 正在分析问题...\n"
    rewritten = await rewrite_query(query)
    yield "\n📚 正在检索文献...\n"

    effective_scope_paper_ids = scope_paper_ids
    if scope_domain_id:
        async for db in get_db():
            result = await db.execute(
                sa_select(PaperDomainAssignment.paper_id)
                .join(Paper, Paper.id == PaperDomainAssignment.paper_id)
                .where(PaperDomainAssignment.domain_id == scope_domain_id)
                .where(Paper.status == "ingested")
            )
            effective_scope_paper_ids = list(result.scalars().all())
            break

    docs = await hybrid_search(rewritten, scope_paper_ids=effective_scope_paper_ids)

    # count unique papers from search results
    unique_paper_ids = set(doc.get("paper_id") for doc in docs if doc.get("paper_id"))
    yield f"\n✅ 已检索到来自 {len(unique_paper_ids)} 篇文献的 {len(docs)} 个相关段落\n\n"

    # get scoped library count (only successfully ingested papers)
    if effective_scope_paper_ids is not None:
        total_papers = len(effective_scope_paper_ids)
    else:
        total_papers = 0
        async for db in get_db():
            count_result = await db.execute(
                sa_select(func.count()).select_from(Paper).where(Paper.status == "ingested")
            )
            total_papers = count_result.scalar()
            break

    # enrich docs with paper titles from DB
    title_cache = {}
    for doc in docs:
        pid = doc.get("paper_id")
        if pid and pid not in title_cache:
            title_cache[pid] = doc.get("title", "")
            if not title_cache[pid]:
                async for db in get_db():
                    paper = await db.get(Paper, pid)
                    if paper:
                        title_cache[pid] = paper.title
                    break

    # build context with numbered references, dedup by paper_id
    context_parts = []
    cited_docs = {}
    seen_pids = {}
    ref_num = 0
    for doc in docs:
        pid = doc.get("paper_id", "")
        title = title_cache.get(pid, doc.get("title", "未知文献"))
        text = doc.get("text", "")
        heading = doc.get("heading", "")
        if not text:
            continue
        if pid not in seen_pids:
            ref_num += 1
            seen_pids[pid] = ref_num
        num = seen_pids[pid]
        cited_docs[num] = title
        prefix = f"[文献{num}] 《{title}》"
        if heading and heading != title:
            prefix += f" §{heading}"
        context_parts.append(f"{prefix}\n{text}")

    context = "\n\n---\n\n".join(context_parts[:20])

    system_prompt = RAG_SYSTEM_PROMPT + f"\n\n当前文献库共有 {total_papers} 篇文献。如果用户询问文献库大小，请根据此数字回答，不要根据检索到的片段数量回答。"
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history[-6:])
    messages.append({"role": "user", "content": f"文献片段:\n{context}\n\n问题: {query}"})

    llm = get_llm_client()
    async for chunk in llm.chat_stream(messages):
        yield chunk

    if cited_docs:
        yield "\n\n---\n\n**参考文献：**\n\n"
        for num, title in cited_docs.items():
            yield f"{num}. 《{title}》\n\n"
