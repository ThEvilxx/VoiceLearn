import { useCallback, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import type { ConversationMeta } from "../../types";
import { deleteConversation, listConversations } from "../../api/client";

const navLinks = [
  { to: "/documents", label: "Documents", icon: "📄" },
  { to: "/graph", label: "Knowledge Graph", icon: "🕸️" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

interface SidebarProps {
  activeConvId: string | null;
  onConvSelect: (id: string | null) => void;
  refreshKey: number;
}

export function Sidebar({ activeConvId, onConvSelect, refreshKey }: SidebarProps) {
  const [convs, setConvs] = useState<ConversationMeta[]>([]);

  const refresh = useCallback(async () => {
    try {
      setConvs(await listConversations());
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh, refreshKey]);

  const handleNew = async () => {
    onConvSelect(null);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteConversation(id);
      if (activeConvId === id) onConvSelect(null);
      await refresh();
    } catch {
      // silently fail
    }
  };

  return (
    <aside
      style={{
        width: 220,
        background: "#1a1a2e",
        color: "#eee",
        display: "flex",
        flexDirection: "column",
        padding: "1rem 0",
        height: "100%",
      }}
    >
      <h2
        style={{
          fontSize: "1.2rem",
          padding: "0 1rem 1rem",
          borderBottom: "1px solid #333",
          margin: 0,
        }}
      >
        VoiceLearn
      </h2>

      <div style={{ padding: "0.8rem 1rem" }}>
        <button
          onClick={handleNew}
          style={{
            width: "100%",
            padding: "0.5rem",
            border: "1px dashed #555",
            borderRadius: 6,
            background: activeConvId === null ? "#16213e" : "transparent",
            color: "#aaa",
            cursor: "pointer",
            fontSize: "0.85rem",
          }}
        >
          + New Chat
        </button>
      </div>

      {convs.length > 0 && (
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "0 0.5rem",
            borderBottom: "1px solid #333",
          }}
        >
          {convs.map((c) => (
            <div
              key={c.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.4rem 0.5rem",
                marginBottom: 2,
                borderRadius: 6,
                background: c.id === activeConvId ? "#16213e" : "transparent",
                cursor: "pointer",
              }}
              onClick={() => onConvSelect(c.id)}
            >
              <span
                style={{
                  fontSize: "0.82rem",
                  color: c.id === activeConvId ? "#fff" : "#aaa",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flex: 1,
                }}
              >
                {c.title}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(c.id);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#666",
                  cursor: "pointer",
                  padding: "2px 4px",
                  fontSize: "0.7rem",
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      <nav style={{ marginTop: "0.5rem" }}>
        {navLinks.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            style={({ isActive }) => ({
              display: "block",
              padding: "0.6rem 1rem",
              color: isActive ? "#fff" : "#aaa",
              background: isActive ? "#16213e" : "transparent",
              textDecoration: "none",
              fontSize: "0.95rem",
            })}
          >
            {l.icon} {l.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
