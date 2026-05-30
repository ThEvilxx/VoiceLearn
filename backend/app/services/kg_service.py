"""Knowledge graph construction and query service."""

from __future__ import annotations

import json

import networkx as nx
from langchain_core.documents import Document

from app.config import settings
from app.core.kg_extractor import extract_from_documents
from app.core.vector_store import get_vector_store
from app.models.graph import EntityDetail, GraphData, GraphEdge, GraphNode

KG_FILE = settings.data_dir / "knowledge_graph.json"


def _load_graph() -> nx.Graph:
    if KG_FILE.exists():
        data = json.loads(KG_FILE.read_text(encoding="utf-8"))
        return nx.node_link_graph(data)
    return nx.Graph()


def _save_graph(graph: nx.Graph) -> None:
    data = nx.node_link_data(graph)
    KG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_graph_data() -> GraphData:
    graph = _load_graph()
    nodes = [
        GraphNode(
            id=nid,
            label=graph.nodes[nid].get("label", nid),
            type=graph.nodes[nid].get("type", "other"),
            properties=graph.nodes[nid].get("properties", {}),
            document_ids=graph.nodes[nid].get("document_ids", []),
        )
        for nid in graph.nodes
    ]
    edges = [
        GraphEdge(
            id=f"{u}_{v}",
            source=u,
            target=v,
            label=attrs.get("label", ""),
            weight=attrs.get("weight", 1.0),
        )
        for u, v, attrs in graph.edges(data=True)
    ]
    return GraphData(nodes=nodes, edges=edges)


def get_entity_detail(entity_id: str) -> EntityDetail | None:
    graph = _load_graph()
    if entity_id not in graph.nodes:
        return None

    attrs = graph.nodes[entity_id]
    neighbors = [
        {
            "id": n,
            "label": graph.nodes[n].get("label", n),
            "relation": graph.get_edge_data(entity_id, n, {}).get("label", ""),
        }
        for n in graph.neighbors(entity_id)
    ]
    return EntityDetail(
        id=entity_id,
        label=attrs.get("label", entity_id),
        type=attrs.get("type", "other"),
        properties=attrs.get("properties", {}),
        related_documents=[{"id": did} for did in attrs.get("document_ids", [])],
        related_entities=neighbors,
    )


async def build_graph() -> dict:
    graph = _load_graph()
    store = get_vector_store()
    results = store.get()

    doc_ids: set[str] = set()
    for meta in results.get("metadatas", []):
        if meta and "document_id" in meta:
            doc_ids.add(meta["document_id"])

    for doc_id in doc_ids:
        already_processed = any(
            doc_id in graph.nodes[n].get("document_ids", []) for n in graph.nodes
        )
        if already_processed:
            continue

        chunk_results = store.get(where={"document_id": doc_id})
        documents = chunk_results.get("documents", [])
        if not documents:
            continue

        docs = [Document(page_content=d) for d in documents]

        try:
            extracted = await extract_from_documents(docs)
        except Exception:
            continue

        for entity in extracted.get("entities", []):
            eid = entity["id"]
            if eid in graph.nodes:
                graph.nodes[eid]["document_ids"].append(doc_id)
            else:
                graph.add_node(
                    eid,
                    label=entity.get("label", eid),
                    type=entity.get("type", "other"),
                    properties=entity.get("properties", {}),
                    document_ids=[doc_id],
                )

        for rel in extracted.get("relations", []):
            src, tgt = rel["source"], rel["target"]
            if src in graph.nodes and tgt in graph.nodes:
                if graph.has_edge(src, tgt):
                    graph[src][tgt]["weight"] = graph[src][tgt].get("weight", 1) + 1
                else:
                    graph.add_edge(src, tgt, label=rel.get("label", ""), weight=1.0)

    _save_graph(graph)
    return {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()}
