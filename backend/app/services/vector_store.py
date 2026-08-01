"""
Vector store wrapper around ChromaDB.

Embeddings: we use Chroma's bundled ONNXMiniLM_L6_V2 embedding function.
It's the ONNX export of all-MiniLM-L6-v2 — same model family as
sentence-transformers, but runs through onnxruntime instead of pulling in
PyTorch, which keeps the install lightweight (no CUDA/torch download).

Isolation: every chunk is stored with `owner_id` and `document_id` in its
metadata, so retrieval always filters to (a) the requesting user's own
documents and, optionally, (b) one specific document. We use a single
Chroma collection for everything rather than one collection per user/doc —
simpler to manage, and metadata filtering gives us the same isolation.
"""
from typing import List, Optional
from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings
from app.services.chunking import Chunk

_client = None
_collection = None
_embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_client().get_or_create_collection(
            name=settings.chroma_collection_name,
            embedding_function=_embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


@dataclass
class RetrievedChunk:
    text: str
    page_number: int
    document_id: str
    filename: str
    distance: float


def add_chunks(
    document_id: str,
    owner_id: str,
    filename: str,
    chunks: List[Chunk],
) -> int:
    if not chunks:
        return 0

    collection = get_collection()

    ids = [f"{document_id}::{c.chunk_index}" for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "owner_id": owner_id,
            "filename": filename,
            "page_number": c.page_number,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]

    # Chroma embeds `documents` automatically via the collection's embedding_function
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def query(
    query_text: str,
    owner_id: str,
    top_k: Optional[int] = None,
    document_id: Optional[str] = None,
) -> List[RetrievedChunk]:
    collection = get_collection()
    top_k = top_k or settings.top_k_chunks

    where = {"owner_id": owner_id}
    if document_id:
        where = {"$and": [{"owner_id": owner_id}, {"document_id": document_id}]}

    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where=where,
    )

    retrieved: List[RetrievedChunk] = []
    docs = results.get("documents") or [[]]
    metas = results.get("metadatas") or [[]]
    dists = results.get("distances") or [[]]

    for text, meta, dist in zip(docs[0], metas[0], dists[0]):
        retrieved.append(
            RetrievedChunk(
                text=text,
                page_number=meta.get("page_number"),
                document_id=meta.get("document_id"),
                filename=meta.get("filename"),
                distance=dist,
            )
        )
    return retrieved


def delete_document(document_id: str) -> None:
    collection = get_collection()
    collection.delete(where={"document_id": document_id})
