import { useCallback, useEffect, useRef, useState } from "react";
import type { GraphData } from "../types";
import { getGraph, reloadGraph } from "../api/client";

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDone, 4000);
    return () => clearTimeout(timer);
  }, [onDone]);

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        background: "#27ae60",
        color: "#fff",
        padding: "0.8rem 1.3rem",
        borderRadius: 10,
        fontSize: "0.9rem",
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        zIndex: 1000,
        animation: "fadeInUp 0.3s ease",
      }}
    >
      {message}
    </div>
  );
}

export function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
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
      const result = await reloadGraph();
      await fetchGraph();
      setToast(
        `✅ Knowledge graph built — ${result.nodes} entities, ${result.edges} relations`,
      );
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
            background: loading ? "#7ab0e0" : "#4a90d9",
            color: "#fff",
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.85 : 1,
            transition: "background 0.2s",
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
      <p style={{ color: "#666", marginBottom: "0.5rem" }}>
        Entities and their relationships extracted from your documents.
      </p>

      {loading && (
        <p style={{ color: "#888", fontSize: "0.85rem", marginBottom: "1rem" }}>
          正在调用大模型抽取实体与关系，根据文档数量可能需要 1-3 分钟，请稍候...
        </p>
      )}

      {(!data || data.nodes.length === 0) && !loading && (
        <p style={{ color: "#999", textAlign: "center", marginTop: "3rem" }}>
          No knowledge graph yet. Upload documents and click "Refresh Graph".
        </p>
      )}

      <div ref={containerRef} style={{ flex: 1, border: "1px solid #ddd", borderRadius: 8 }} />

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
