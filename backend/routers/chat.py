"""AI chat router — SSE chat, config CRUD, conversation CRUD."""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.auth import get_db
from backend.models import Conversation
from backend.schemas import ChatRequest, ConversationCreate
from backend.services.ai_service import (
    load_ai_config,
    mask_api_key,
    stream_chat,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── AI Config ──────────────────────────────────────────────────

@router.get("/config")
async def get_config(data_dir: str = Depends(get_db)):
    """Get AI configuration (API key masked)."""
    config = load_ai_config()
    return mask_api_key(config)


@router.put("/config")
async def update_config(data_dir: str = Depends(get_db)):
    """AI config is managed via environment variables, not this endpoint."""
    return {"detail": "AI 配置请通过环境变量 EASYFUND_AI_* 设置，详见 .env.example"}


# ── Conversations ──────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(data_dir: str = Depends(get_db)):
    """List all conversations (summary, no messages)."""
    convs = await Conversation.all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "message_count": len(c.messages or []),
        }
        for c in convs
    ]


@router.post("/conversations", status_code=201)
async def create_conversation(data: ConversationCreate, data_dir: str = Depends(get_db)):
    """Create a new conversation."""
    now = datetime.now(timezone.utc).isoformat()
    conv = await Conversation.create(
        id=f"conv-{uuid.uuid4().hex[:8]}",
        title=data.title,
        messages=[],
        created_at=now,
        updated_at=now,
    )
    return conv.to_dict()


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, data_dir: str = Depends(get_db)):
    """Get conversation with messages."""
    conv = await Conversation.get_or_none(id=conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv.to_dict()


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, data_dir: str = Depends(get_db)):
    """Delete a conversation."""
    conv = await Conversation.get_or_none(id=conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    await conv.delete()
    return {"ok": True}


# ── Chat (SSE) ─────────────────────────────────────────────────

@router.post("")
async def chat(req: ChatRequest, data_dir: str = Depends(get_db)):
    """Send a message and stream AI response via SSE."""
    # Load conversation
    conv = await Conversation.get_or_none(id=req.conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    # Add user message
    now = datetime.now(timezone.utc).isoformat()
    messages = conv.messages or []
    user_msg = {"role": "user", "content": req.message}
    messages.append(user_msg)
    conv.updated_at = now

    # Build messages for AI (preserve OpenAI format for tool_calls/tool results)
    ai_messages = []
    for m in messages:
        msg = {"role": m["role"]}
        content = m.get("content")
        if content is not None:
            msg["content"] = content
        else:
            msg["content"] = None
        if m.get("tool_calls"):
            msg["tool_calls"] = m["tool_calls"]
        if m.get("tool_call_id"):
            msg["tool_call_id"] = m["tool_call_id"]
        if m.get("name"):
            msg["name"] = m["name"]
        ai_messages.append(msg)

    # Stream response
    async def generate():
        assistant_content = ""
        tool_calls_records = []  # OpenAI format: {id, type, function: {name, arguments}}
        tool_results = []  # tool result messages for conversation

        async for event_str in stream_chat(ai_messages):
            yield event_str

            # Parse event to track assistant response for persistence
            if event_str.startswith("event: content\n"):
                data_line = event_str.split("\n")[1]
                if data_line.startswith("data: "):
                    try:
                        data = json.loads(data_line[6:])
                        assistant_content += data.get("text", "")
                    except Exception:
                        pass

            if event_str.startswith("event: tool_call\n"):
                data_line = event_str.split("\n")[1]
                if data_line.startswith("data: "):
                    try:
                        data = json.loads(data_line[6:])
                        tool_calls_records.append({
                            "id": data.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": data.get("name", ""),
                                "arguments": data.get("arguments", "{}"),
                            },
                        })
                    except Exception:
                        pass

            if event_str.startswith("event: tool_result\n"):
                data_line = event_str.split("\n")[1]
                if data_line.startswith("data: "):
                    try:
                        data = json.loads(data_line[6:])
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": data.get("id", ""),
                            "content": json.dumps(data.get("result", {}), ensure_ascii=False, default=str),
                        })
                    except Exception:
                        pass

        # Save assistant message to conversation
        assistant_msg = {
            "role": "assistant",
            "content": assistant_content or None,
        }
        if tool_calls_records:
            assistant_msg["tool_calls"] = tool_calls_records
        messages.append(assistant_msg)

        # Save tool result messages
        for tr in tool_results:
            messages.append(tr)

        # Auto-generate title from first user message
        if len(messages) <= 2 and conv.title == "新对话":
            conv.title = req.message[:30] + ("..." if len(req.message) > 30 else "")

        conv.messages = messages
        conv.updated_at = datetime.now(timezone.utc).isoformat()
        await conv.save()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
