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
    // 1. 拦截空状态：没有 DOM 容器或没有节点数据，直接不执行
    if (!containerRef.current || !data || !data.nodes || data.nodes.length === 0) {
      return;
    }

    // 2. 销毁旧实例，防止重入报错
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    // 3. 暴力清洗节点：强制转换 id/label 为 vis-network 能识别的字符串
    const safeNodes = data.nodes.map((n) => ({
      ...n,
      id: String(n.id),
      label: String(n.label || n.id || "Unknown"),
      group: n.type,
    }));

    const validNodeIds = new Set(safeNodes.map((n) => n.id));

    // 4. 暴力清洗连线：强制映射 from/to + 强制过滤幽灵边 + 强制转字符串
    const safeEdges = (data.edges || [])
      .map((e) => {
        const raw = e as unknown as Record<string, unknown>;
        return {
          id: raw.id as string,
          from: String(raw.from || e.source),
          to: String(raw.to || e.target),
          label: e.label,
          width: Math.min(((raw.weight as number) || 1) * 2, 5),
        };
      })
      .filter((e) => validNodeIds.has(e.from) && validNodeIds.has(e.to));

    const finalData = { nodes: safeNodes, edges: safeEdges };

    let cancelled = false;

    const renderGraph = async () => {
      const { Network } = await import("vis-network");
      if (cancelled) return;

      try {
        networkRef.current = new Network(containerRef.current!, finalData, {
          nodes: { shape: "dot", size: 16, font: { size: 12 } },
          edges: { arrows: "to", font: { size: 10, align: "middle" } },
          physics: { solver: "forceAtlas2Based" },
        });
      } catch (err) {
        console.error("vis-network 初始化彻底崩溃:", err);
      }
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
