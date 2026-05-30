import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Chat", icon: "💬" },
  { to: "/documents", label: "Documents", icon: "📄" },
  { to: "/graph", label: "Knowledge Graph", icon: "🕸️" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

export function Sidebar() {
  return (
    <aside
      style={{
        width: 200,
        background: "#1a1a2e",
        color: "#eee",
        display: "flex",
        flexDirection: "column",
        padding: "1rem 0",
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
      <nav style={{ marginTop: "1rem" }}>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === "/"}
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
