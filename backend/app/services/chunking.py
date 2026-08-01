"""
Chunking strategy
------------------
We split page text into overlapping character-window chunks, but we don't
cut blindly at a fixed offset: we snap the boundary to the nearest sentence
or paragraph break within a small lookback window so chunks stay
semantically coherent (a chunk shouldn't end mid-sentence if we can help it).

Overlap (default 150 chars) means a fact sitting near a chunk boundary
still appears in full inside at least one chunk, instead of being split
across two chunks and losing retrievability in either.

Each chunk keeps its source page number as metadata, which is what lets
us cite "page 4" instead of just "somewhere in the document."
"""
from dataclasses import dataclass
from typing import List

from app.config import settings

SENTENCE_ENDERS = (". ", "! ", "? ", "\n\n")


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int


def _find_break_point(text: str, target: int, lookback: int = 120) -> int:
    """Search backwards from `target` for a natural sentence/paragraph break.
    Falls back to `target` (hard cut) if none is found nearby."""
    window_start = max(0, target - lookback)
    window = text[window_start:target]

    best = -1
    for ender in SENTENCE_ENDERS:
        idx = window.rfind(ender)
        if idx != -1:
            best = max(best, window_start + idx + len(ender))

    return best if best != -1 else target


def chunk_page_text(
    text: str,
    page_number: int,
    chunk_size: int = None,
    chunk_overlap: int = None,
    start_index: int = 0,
) -> List[Chunk]:
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    text = text.strip()
    if not text:
        return []

    chunks: List[Chunk] = []
    start = 0
    idx = start_index

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            end = _find_break_point(text, end)

        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(text=piece, page_number=page_number, chunk_index=idx))
            idx += 1

        if end >= len(text):
            break

        # step forward, backing off by the overlap amount
        start = max(end - chunk_overlap, start + 1)

    return chunks


def chunk_document(pages: List[str]) -> List[Chunk]:
    """pages: list of raw text per page, 1-indexed page numbers implied by position."""
    all_chunks: List[Chunk] = []
    next_index = 0
    for page_number, page_text in enumerate(pages, start=1):
        page_chunks = chunk_page_text(page_text, page_number, start_index=next_index)
        all_chunks.extend(page_chunks)
        next_index += len(page_chunks)
    return all_chunks
