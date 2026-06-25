from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
import json

from backend.models.database import User, Conversation, Message, get_db
from backend.models.schemas import ConversationCreate, ConversationOut, MessageOut
from backend.services.auth import get_current_user
from backend.services.rag_service import generate_answer_stream

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(user: User = Depends(get_current_user)):
    async for db in get_db():
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
        )
        convos = result.scalars().all()
        return [ConversationOut.model_validate(c) for c in convos]


@router.post("")
async def create_conversation(request: ConversationCreate, user: User = Depends(get_current_user)):
    async for db in get_db():
        convo = Conversation(user_id=user.id, title=request.title)
        db.add(convo)
        await db.commit()
        return ConversationOut.model_validate(convo)


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, user: User = Depends(get_current_user)):
    async for db in get_db():
        convo = await db.get(Conversation, conversation_id)
        if not convo or convo.user_id != user.id:
            raise HTTPException(status_code=404, detail="对话不存在")
        await db.delete(convo)
        await db.commit()
        return {"deleted": conversation_id}


@router.get("/{conversation_id}/messages")
async def list_messages(conversation_id: str, user: User = Depends(get_current_user)):
    async for db in get_db():
        convo = await db.get(Conversation, conversation_id)
        if not convo or convo.user_id != user.id:
            raise HTTPException(status_code=404, detail="对话不存在")
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        return [MessageOut.model_validate(m) for m in messages]


@router.post("/{conversation_id}/messages")
async def send_message(conversation_id: str, body: dict, user: User = Depends(get_current_user)):
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    async for db in get_db():
        convo = await db.get(Conversation, conversation_id)
        if not convo or convo.user_id != user.id:
            raise HTTPException(status_code=404, detail="对话不存在")

        # Save user message
        db.add(Message(conversation_id=conversation_id, role="user", content=query))
        # Update conversation title from first message
        if convo.title == "新对话":
            convo.title = query[:60] + ("..." if len(query) > 60 else "")
        await db.commit()
        break

    scope_paper_ids = body.get("scope_paper_ids") or None
    scope_domain_id = body.get("scope_domain_id") or None

    async def event_stream():
        full_response = ""
        citations = None
        try:
            async for chunk in generate_answer_stream(
                query,
                scope_paper_ids=scope_paper_ids,
                scope_domain_id=scope_domain_id,
            ):
                if chunk:
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                    if not chunk.startswith(("🔍", "\n📚", "\n✅", "📚", "✅")):
                        full_response += chunk
        except Exception as exc:
            yield f"data: [回答出错：{exc}]\n\n"

        # Save AI response
        async for db in get_db():
            db.add(Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                citations=citations,
            ))
            await db.commit()
            break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
