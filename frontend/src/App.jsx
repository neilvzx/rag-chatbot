import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000";

function useAuth() {
  const [token, setToken] = useState(localStorage.getItem("rag_token") || "");

  useEffect(() => {
    if (token) localStorage.setItem("rag_token", token);
    else localStorage.removeItem("rag_token");
  }, [token]);

  return { token, setToken };
}

function AuthForm({ onAuthed }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      let res;
      if (mode === "register") {
        res = await fetch(`${API_BASE}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
      } else {
        const form = new URLSearchParams();
        form.set("username", email);
        form.set("password", password);
        res = await fetch(`${API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: form,
        });
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      onAuthed(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.authCard}>
      <h2>{mode === "login" ? "Log in" : "Create account"}</h2>
      <form onSubmit={submit} style={styles.form}>
        <input
          style={styles.input}
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          style={styles.input}
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <div style={styles.error}>{error}</div>}
        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? "..." : mode === "login" ? "Log in" : "Register"}
        </button>
      </form>
      <button
        style={styles.linkButton}
        onClick={() => setMode(mode === "login" ? "register" : "login")}
      >
        {mode === "login"
          ? "Need an account? Register"
          : "Already have an account? Log in"}
      </button>
    </div>
  );
}

function UploadPanel({ token, onUploaded }) {
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    setStatus("Uploading and processing...");
    setError("");

    const form = new FormData();
    form.set("file", file);

    try {
      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Upload failed (${res.status})`);
      }
      const data = await res.json();
      setStatus(
        `"${data.filename}" ready — ${data.num_pages} page(s), ${data.num_chunks} chunk(s)`
      );
      onUploaded?.(data);
    } catch (err) {
      setError(err.message);
      setStatus("");
    }
  }

  return (
    <div style={styles.uploadPanel}>
      <label style={styles.uploadLabel}>
        Upload a PDF
        <input
          type="file"
          accept="application/pdf"
          onChange={handleFile}
          style={{ display: "none" }}
        />
      </label>
      {status && <div style={styles.status}>{status}</div>}
      {error && <div style={styles.error}>{error}</div>}
    </div>
  );
}

function ChatPanel({ token }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  async function ask(e) {
    e.preventDefault();
    if (!question.trim()) return;

    const q = question;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Query failed (${res.status})`);
      }
      const data = await res.json();
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.answer, sources: data.sources },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `Error: ${err.message}`, sources: [] },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.chatPanel}>
      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            Upload a document, then ask a question about it.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              ...styles.message,
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              background: m.role === "user" ? "#2563eb" : "#f1f5f9",
              color: m.role === "user" ? "white" : "#0f172a",
            }}
          >
            <div>{m.text}</div>
            {m.sources && m.sources.length > 0 && (
              <div style={styles.sources}>
                {m.sources.map((s, j) => (
                  <div key={j} style={styles.sourceChip}>
                    {s.filename}
                    {s.page_number != null ? ` (p.${s.page_number})` : ""}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div style={styles.emptyState}>Thinking...</div>}
      </div>
      <form onSubmit={ask} style={styles.chatForm}>
        <input
          style={styles.input}
          placeholder="Ask a question about your documents..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button style={styles.button} type="submit" disabled={loading}>
          Send
        </button>
      </form>
    </div>
  );
}

export default function App() {
  const { token, setToken } = useAuth();

  if (!token) {
    return (
      <div style={styles.page}>
        <AuthForm onAuthed={setToken} />
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.title}>Document Q&A</h1>
        <button style={styles.linkButton} onClick={() => setToken("")}>
          Log out
        </button>
      </div>
      <UploadPanel token={token} />
      <ChatPanel token={token} />
    </div>
  );
}

const styles = {
  page: {
    maxWidth: 720,
    margin: "0 auto",
    padding: "32px 16px",
    fontFamily: "system-ui, sans-serif",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  title: { margin: 0, fontSize: 22 },
  authCard: {
    maxWidth: 360,
    margin: "80px auto",
    padding: 24,
    border: "1px solid #e2e8f0",
    borderRadius: 12,
  },
  form: { display: "flex", flexDirection: "column", gap: 10 },
  input: {
    padding: "10px 12px",
    border: "1px solid #cbd5e1",
    borderRadius: 8,
    fontSize: 14,
  },
  button: {
    padding: "10px 16px",
    background: "#2563eb",
    color: "white",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
  },
  linkButton: {
    background: "none",
    border: "none",
    color: "#2563eb",
    cursor: "pointer",
    fontSize: 13,
    marginTop: 10,
    padding: 0,
  },
  error: { color: "#dc2626", fontSize: 13 },
  status: { color: "#16a34a", fontSize: 13 },
  uploadPanel: {
    padding: 16,
    border: "1px dashed #cbd5e1",
    borderRadius: 10,
    marginBottom: 16,
  },
  uploadLabel: {
    display: "inline-block",
    padding: "8px 14px",
    background: "#f1f5f9",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
  },
  chatPanel: {
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    display: "flex",
    flexDirection: "column",
    height: 480,
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  emptyState: { color: "#94a3b8", fontSize: 14, textAlign: "center" },
  message: {
    maxWidth: "80%",
    padding: "10px 14px",
    borderRadius: 10,
    fontSize: 14,
  },
  sources: {
    marginTop: 8,
    display: "flex",
    gap: 6,
    flexWrap: "wrap",
  },
  sourceChip: {
    fontSize: 11,
    background: "rgba(0,0,0,0.08)",
    padding: "2px 8px",
    borderRadius: 6,
  },
  chatForm: {
    display: "flex",
    gap: 8,
    padding: 12,
    borderTop: "1px solid #e2e8f0",
  },
};
