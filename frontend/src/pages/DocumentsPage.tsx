import { useCallback, useEffect, useRef, useState } from "react";
import type { DocumentInfo } from "../types";
import { deleteDocument, listDocuments, uploadDocument } from "../api/client";

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDone, 3500);
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

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments());
    } catch {
      setError("Failed to load documents");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await uploadDocument(file);
      await refresh();
      setToast(`✅ ${file.name} uploaded — ${docs.length + 1} documents indexed`);
    } catch {
      setError("Upload failed. Check file format and try again.");
    } finally {
      setUploading(false);
      // Reset the file input so the same file can be re-uploaded
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      await refresh();
    } catch {
      setError("Delete failed");
    }
  };

  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      <h2>Documents</h2>
      <p style={{ color: "#666", marginBottom: "1rem" }}>
        Upload course notes, papers (PDF, Markdown, TXT, source code) to build your
        learning knowledge base.
      </p>

      <label
        style={{
          display: "inline-block",
          padding: "0.7rem 1.5rem",
          background: uploading ? "#7ab0e0" : "#4a90d9",
          color: "#fff",
          borderRadius: 8,
          cursor: uploading ? "default" : "pointer",
          fontSize: "0.95rem",
          opacity: uploading ? 0.85 : 1,
          transition: "background 0.2s",
        }}
      >
        {uploading ? (
          <>
            <span className="spinner" /> Uploading...
          </>
        ) : (
          "Upload Document"
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.md,.txt,.py,.js,.ts,.tsx,.jsx,.go,.rs,.java,.cpp,.c"
          onChange={handleUpload}
          disabled={uploading}
          hidden
        />
      </label>

      {uploading && (
        <p style={{ color: "#888", fontSize: "0.85rem", marginTop: 10 }}>
          正在解析文件并生成向量索引，根据文件大小可能需要 1-3 分钟，请稍候...
        </p>
      )}

      {error && <p style={{ color: "#e74c3c", marginTop: 8 }}>{error}</p>}

      {docs.length === 0 && (
        <p style={{ marginTop: "2rem", color: "#999" }}>
          No documents yet. Upload one to get started.
        </p>
      )}

      <ul style={{ marginTop: "1.5rem", listStyle: "none", padding: 0 }}>
        {docs.map((d) => (
          <li
            key={d.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.7rem 0",
              borderBottom: "1px solid #eee",
            }}
          >
            <span>
              📄 {d.name}{" "}
              <span style={{ color: "#999", fontSize: "0.8rem" }}>
                ({d.file_type}, {d.chunk_count} chunks)
              </span>
            </span>
            <button
              onClick={() => handleDelete(d.id)}
              style={{
                background: "none",
                border: "none",
                color: "#e74c3c",
                cursor: "pointer",
              }}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
