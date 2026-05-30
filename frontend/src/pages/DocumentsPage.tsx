import { useCallback, useEffect, useState } from "react";
import type { DocumentInfo } from "../types";
import { deleteDocument, listDocuments, uploadDocument } from "../api/client";

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments());
    } catch {
      setError("Failed to load documents");
    }
  }, []);

  useEffect(() => {
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
    } catch {
      setError("Upload failed. Check file format and try again.");
    } finally {
      setUploading(false);
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
          background: "#4a90d9",
          color: "#fff",
          borderRadius: 8,
          cursor: "pointer",
          fontSize: "0.95rem",
        }}
      >
        {uploading ? "Uploading..." : "Upload Document"}
        <input
          type="file"
          accept=".pdf,.md,.txt,.py,.js,.ts,.tsx,.jsx,.go,.rs,.java,.cpp,.c"
          onChange={handleUpload}
          hidden
        />
      </label>

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
    </div>
  );
}
