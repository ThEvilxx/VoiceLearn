import { useCallback, useEffect, useRef, useState } from "react";
import { Network } from "vis-network";
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

  // Render knowledge graph with hardened data-cleaning pipeline
  useEffect(() => {
    if (!containerRef.current || !data) return;

    if (!Array.isArray(data.nodes)) {
      console.warn("🚨 数据就绪，但 nodes 不是数组！当前数据为:", data);
      return;
    }

    try {
      // Strip all nested properties, keep only id + label as strings
      const safeNodes = data.nodes.map((n) => ({
        id: String(n.id),
        label: String(n.label || n.id || "Unknown"),
      }));

      const validIds = new Set(safeNodes.map((n) => n.id));

      // Remap source/target → from/to, drop ghost edges
      const rawEdges: Record<string, unknown>[] = (data.edges || []) as any;
      const safeEdges = rawEdges
        .map((e) => ({
          from: String(e.from || e.source),
          to: String(e.to || e.target),
          label: e.label ? String(e.label) : undefined,
          font: { size: 12, align: "middle" as const },
        }))
        .filter((e) => validIds.has(e.from) && validIds.has(e.to));

      const finalData = { nodes: safeNodes, edges: safeEdges };

      const options = {
        nodes: {
          shape: "box" as const,
          margin: { top: 10, right: 10, bottom: 10, left: 10 },
          font: { size: 14, color: "#333333" },
          color: {
            background: "#E3F2FD",
            border: "#2196F3",
            highlight: { background: "#BBDEFB", border: "#1976D2" },
          },
          borderWidth: 2,
          shadow: true,
        },
        edges: {
          width: 1.5,
          color: { color: "#999999", highlight: "#2196F3" },
          arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          smooth: { enabled: true, type: "continuous" as const, roundness: 0.5 },
        },
        physics: {
          barnesHut: { gravitationalConstant: -2000, springLength: 150 },
          stabilization: { iterations: 150 },
        },
      };

      const network = new Network(containerRef.current, finalData, options);

      return () => {
        network.destroy();
      };
    } catch (error) {
      console.error("💥 vis-network 渲染时发生致命崩溃：", error);
    }
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

      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: "calc(100vh - 120px)",
          minHeight: "400px",
        }}
      />

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
