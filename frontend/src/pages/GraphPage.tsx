import { useCallback, useEffect, useRef, useState } from "react";
import type { GraphData } from "../types";
import { getGraph, reloadGraph } from "../api/client";

export function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchGraph = useCallback(async () => {
    try {
      setData(await getGraph());
    } catch {
      /* graph not built yet */
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchGraph();
  }, [fetchGraph]);

  const handleReload = async () => {
    setLoading(true);
    try {
      await reloadGraph();
      await fetchGraph();
    } finally {
      setLoading(false);
    }
  };

  // Render knowledge graph using vis-network
  useEffect(() => {
    if (!data || !containerRef.current) return;

    const renderGraph = async () => {
      const { Network } = await import("vis-network");
      const { DataSet } = await import("vis-data");

      const nodes = new DataSet(
        data.nodes.map((n) => ({
          id: n.id,
          label: n.label,
          group: n.type,
        })),
      );
      const edges = new DataSet(
        data.edges.map((e) => ({
          id: e.id,
          from: e.source,
          to: e.target,
          label: e.label,
          width: Math.min(e.weight * 2, 5),
        })),
      );

      new Network(containerRef.current!, { nodes, edges }, {
        nodes: { shape: "dot", size: 16, font: { size: 12 } },
        edges: { arrows: "to", font: { size: 10, align: "middle" } },
        physics: { solver: "forceAtlas2Based" },
      });
    };

    renderGraph();
  }, [data]);

  return (
    <div style={{ padding: "2rem", height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Knowledge Graph</h2>
        <button
          onClick={handleReload}
          disabled={loading}
          style={{
            padding: "0.5rem 1rem",
            borderRadius: 8,
            border: "none",
            background: "#4a90d9",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          {loading ? (
            <>
              <span className="spinner" /> Building...
            </>
          ) : (
            "Refresh Graph"
          )}
        </button>
      </div>
      <p style={{ color: "#666", marginBottom: "1rem" }}>
        Entities and their relationships extracted from your documents.
      </p>

      {(!data || data.nodes.length === 0) && !loading && (
        <p style={{ color: "#999", textAlign: "center", marginTop: "3rem" }}>
          No knowledge graph yet. Upload documents and click "Refresh Graph".
        </p>
      )}

      <div ref={containerRef} style={{ flex: 1, border: "1px solid #ddd", borderRadius: 8 }} />
    </div>
  );
}
