"""Knowledge graph data models."""

from __future__ import annotations

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict
    document_ids: list[str]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    weight: float


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class EntityDetail(BaseModel):
    id: str
    label: str
    type: str
    properties: dict
    related_documents: list[dict]
    related_entities: list[dict]
