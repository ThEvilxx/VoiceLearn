"""Conversation management API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.conversation_service import (
    create_conversation,
    delete_conversation,
    get_messages,
    list_conversations,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_convs():
    return await list_conversations()


@router.post("")
async def create_conv():
    conv_id = await create_conversation()
    return {"conversation_id": conv_id}


@router.get("/{conv_id}")
async def get_conv(conv_id: str):
    msgs = await get_messages(conv_id)
    return {"conversation_id": conv_id, "messages": msgs}


@router.delete("/{conv_id}")
async def delete_conv(conv_id: str):
    if not await delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "conversation_id": conv_id}
