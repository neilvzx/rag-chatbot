# Document Q&A / RAG Chatbot

Upload PDF documents, ask questions in natural language, and get answers
grounded in the actual document content — with citations back to the
source, not hallucinated answers.

Built to demonstrate a full retrieval-augmented generation (RAG) pipeline
end-to-end: chunking strategy, vector search, and grounded LLM generation —
not just prompt engineering wrapped around an API call.

## How it works

1. **Ingestion** — a PDF is parsed page-by-page, split into overlapping
   chunks (snapped to sentence/paragraph boundaries rather than cutting
   mid-sentence), embedded locally via ChromaDB's built-in ONNX embedding
   model, and stored in a per-user ChromaDB collection. Metadata (filename,
   page number, owner) is tracked in Postgres alongside each document.
2. **Retrieval + generation** — a question is embedded and matched against
   the top-k most similar chunks in ChromaDB. Those chunks are passed as
   context to Groq (Llama) with an instruction to answer only from the
   provided sources and cite them inline — reducing hallucination instead
   of just generating a plausible-sounding answer.
3. **Auth** — JWT-based register/login (bcrypt-hashed passwords). All
   documents and queries are scoped to the authenticated user.
4. **Frontend** — a React (Vite) single-page app: login/register, PDF
   upload, and a chat interface showing the answer alongside which source
   chunks it was grounded in.
5. **Docker** — the full stack (Postgres, FastAPI backend, React frontend)
   runs with a single `docker compose up`.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI |
| Vector DB | ChromaDB (local, ONNX embeddings — no GPU/PyTorch required) |
| LLM | Groq (Llama) |
| PDF parsing | pdfplumber |
| Relational DB | PostgreSQL + SQLAlchemy |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Frontend | React + Vite |
| Containerization | Docker Compose |

## Running it

**Requirements:** Docker Desktop, a [Groq API key](https://console.groq.com).

```bash
git clone <your-repo-url>
cd rag-chatbot

# add your Groq API key
echo "GROQ_API_KEY=your_key_here" > .env

docker compose up -d

# first run only: create the database tables
docker compose exec backend python3 -c \
  "from app.db.base import Base; from app.db.session import engine; from app.models import user, document; Base.metadata.create_all(engine)"
```

Then open:
- **Frontend:** http://localhost:5173
- **API docs (Swagger):** http://localhost:8000/docs

## API overview

| Endpoint | Description |
|---|---|
| `POST /auth/register` | Create an account |
| `POST /auth/login` | Get a JWT access token |
| `POST /documents/upload` | Upload and ingest a PDF (auth required) |
| `GET /documents/{id}` | Check ingestion status of a document |
| `POST /query` | Ask a question, get a grounded answer with sources (auth required) |

## Design notes

- **Chunking** snaps boundaries to sentences/paragraphs with overlap between
  chunks, rather than a naive fixed-character split — this preserves
  semantic coherence within each chunk, which materially improves
  retrieval quality.
- **Embeddings run locally** via ChromaDB's ONNX-based default embedding
  function rather than `sentence-transformers`/PyTorch, keeping the image
  small and avoiding a GPU dependency.
- **Every answer is grounded**: the system prompt instructs the model to
  answer only from retrieved context and to say so explicitly when the
  answer isn't in the documents, rather than guessing.

## Possible extensions

- Persist conversation history per user
- Support additional file types (docx, txt, markdown)
- Streaming responses
- Multi-document cross-referencing in a single query
