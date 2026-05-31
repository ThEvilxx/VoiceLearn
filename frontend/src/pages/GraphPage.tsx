import { useCallback, useEffect, useRef, useState } from "react";
import type { Network } from "vis-network";
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
  const networkRef = useRef<Network | null>(null);

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
    if (!containerRef.current || !data || !data.nodes.length) return;

    // Destroy previous instance to prevent duplicate / stale render
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    let cancelled = false;

    const renderGraph = async () => {
      const [{ Network }, { DataSet }] = await Promise.all([
        import("vis-network"),
        import("vis-data"),
      ]);

      if (cancelled) return;

      console.log("1. 图谱原始数据: ", data);
      console.log("2. 节点第一项: ", data.nodes[0]);
      console.log("3. 容器高度: ", containerRef.current?.clientHeight, " 宽度: ", containerRef.current?.clientWidth);

      // 质检：检测幽灵连线（source/target 指向不存在的节点 ID）
      console.log("第一条连线数据:", data.edges[0]);

      const nodeIds = new Set(data.nodes.map((n) => n.id));
      const badEdges = data.edges.filter(
        (e) => !nodeIds.has(e.source) || !nodeIds.has(e.target),
      );

      let cleanEdges = data.edges;
      if (badEdges.length > 0) {
        console.error(
          "🚨 发现幽灵连线！以下连线指向了不存在的节点，这将导致 vis-network 白屏:",
          badEdges,
        );
        cleanEdges = data.edges.filter(
          (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
        );
        console.log("✅ 自动过滤坏连线完毕，尝试重新渲染...");
      } else {
        console.log("✅ 所有连线质检通过，没有幽灵连线");
      }

      const nodes = new DataSet(
        data.nodes.map((n) => ({
          id: n.id,
          label: n.label,
          group: n.type,
        })),
      );
      const edges = new DataSet(
        cleanEdges.map((e) => ({
          id: e.id,
          from: e.source,
          to: e.target,
          label: e.label,
          width: Math.min(e.weight * 2, 5),
        })),
      );

      networkRef.current = new Network(containerRef.current!, { nodes, edges }, {
        nodes: { shape: "dot", size: 16, font: { size: 12 } },
        edges: { arrows: "to", font: { size: 10, align: "middle" } },
        physics: { solver: "forceAtlas2Based" },
      });
    };

    renderGraph();

    return () => {
      cancelled = true;
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
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
