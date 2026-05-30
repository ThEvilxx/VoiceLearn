"""Knowledge graph API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.kg_service import build_graph, get_entity_detail, get_graph_data

router = APIRouter(prefix="/api/graph", tags=["knowledge-graph"])


@router.get("")
async def get_graph():
    return get_graph_data().model_dump()


@router.get("/entity/{entity_id}")
async def get_entity(entity_id: str):
    detail = get_entity_detail(entity_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return detail.model_dump()


@router.post("/reload")
async def reload_graph():
    result = await build_graph()
    return result
