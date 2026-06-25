from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.models.schemas import ChatRequest
from backend.services.rag_service import generate_answer_stream

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(request: ChatRequest):
    async def event_stream():
        try:
            async for chunk in generate_answer_stream(
                request.query,
                scope_paper_ids=request.scope_paper_ids or None,
                scope_domain_id=request.scope_domain_id,
            ):
                if chunk:
                    data = chunk.replace("\n", "\ndata: ")
                    yield f"data: {data}\n\n"
        except Exception as exc:
            yield f"data: [回答出错：{exc}]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
