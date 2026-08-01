from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import documents
from app.routers import query
from app.routers import auth
from app.models import user, document

app = FastAPI(title="RAG Document Q&A")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)


@app.get("/health")
def health():
    return {"status": "ok"}
