from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.deps import get_current_user
from app.models.user import User
from app.services import vector_store
from app.services.groq_client import generate_answer, GroqError

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    top_k: Optional[int] = None


class SourceOut(BaseModel):
    filename: str
    page_number: Optional[int]
    document_id: str
    distance: float
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


@router.post("", response_model=QueryResponse)
def query_documents(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    if not payload.question or not payload.question.strip():
        raise HTTPException(400, "question must not be empty")

    retrieved = vector_store.query(
        query_text=payload.question,
        owner_id=str(current_user.id),
        top_k=payload.top_k,
        document_id=payload.document_id,
    )

    if not retrieved:
        return QueryResponse(
            answer="I couldn't find any relevant content in your documents to answer that.",
            sources=[],
        )

    context_chunks = [chunk.text for chunk in retrieved]

    try:
        answer = generate_answer(payload.question, context_chunks)
    except GroqError as e:
        raise HTTPException(502, str(e))

    sources = [
        SourceOut(
            filename=chunk.filename,
            page_number=chunk.page_number,
            document_id=chunk.document_id,
            distance=chunk.distance,
            excerpt=chunk.text[:200] + ("..." if len(chunk.text) > 200 else ""),
        )
        for chunk in retrieved
    ]

    return QueryResponse(answer=answer, sources=sources)
