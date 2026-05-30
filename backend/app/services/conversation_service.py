"""Conversation memory: CRUD + sliding-window history management."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select, update

from app.db.database import async_session
from app.db.models import Conversation, Message

MAX_TURNS = 10  # sliding window size (user+assistant = 1 turn each)


async def create_conversation(title: str = "New Chat") -> str:
    conv_id = uuid.uuid4().hex[:12]
    async with async_session() as db:
        db.add(Conversation(id=conv_id, title=title[:200]))
        await db.commit()
    return conv_id


async def list_conversations() -> list[dict]:
    async with async_session() as db:
        result = await db.execute(
            select(Conversation).order_by(Conversation.updated_at.desc())
        )
        convs = result.scalars().all()
        return [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ]


async def get_messages(conversation_id: str) -> list[dict]:
    async with async_session() as db:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        msgs = result.scalars().all()
        return [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in msgs
        ]


async def add_message(
    conversation_id: str, role: str, content: str
) -> None:
    async with async_session() as db:
        db.add(
            Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
            )
        )
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now())
        )
        await db.commit()

    await _trim_old_messages(conversation_id)


async def delete_conversation(conversation_id: str) -> bool:
    async with async_session() as db:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            return False
        await db.delete(conv)
        await db.commit()
    return True


async def build_history_context(
    conversation_id: str, max_turns: int = MAX_TURNS
) -> str:
    """Format recent messages as a string for the LLM prompt."""
    msgs = await get_messages(conversation_id)
    recent = msgs[-(max_turns * 2) :]

    if not recent:
        return ""

    lines: list[str] = []
    for m in recent:
        role = "Student" if m["role"] == "user" else "Tutor"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


async def _trim_old_messages(conversation_id: str) -> None:
    """Keep only the most recent (MAX_TURNS * 2) messages."""
    async with async_session() as db:
        result = await db.execute(
            select(Message.id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
        )
        all_ids = [row[0] for row in result.all()]
        if len(all_ids) <= MAX_TURNS * 2:
            return
        ids_to_delete = all_ids[MAX_TURNS * 2 :]
        await db.execute(delete(Message).where(Message.id.in_(ids_to_delete)))
        await db.commit()
