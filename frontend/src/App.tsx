import { useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/Layout/Sidebar";
import { ChatPage } from "./pages/ChatPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { GraphPage } from "./pages/GraphPage";
import { SettingsPage } from "./pages/SettingsPage";
import "./App.css";

export default function App() {
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);

  const handleConvChange = (id: string) => {
    if (id !== activeConvId) {
      setActiveConvId(id);
      setSidebarRefresh((n) => n + 1);
    }
  };

  return (
    <BrowserRouter>
      <div style={{ display: "flex", height: "100vh" }}>
        <Sidebar
          activeConvId={activeConvId}
          onConvSelect={setActiveConvId}
          refreshKey={sidebarRefresh}
        />
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <Routes>
            <Route
              path="/"
              element={
                <ChatPage
                  activeConvId={activeConvId}
                  onConvChange={handleConvChange}
                />
              }
            />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
