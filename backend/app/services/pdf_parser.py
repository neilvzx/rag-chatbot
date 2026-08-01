from typing import List
import pdfplumber


class PDFParseError(Exception):
    pass


def extract_pages(file_path: str) -> List[str]:
    """Returns a list of raw text strings, one per page (index 0 = page 1)."""
    pages: List[str] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
    except Exception as e:
        raise PDFParseError(f"Failed to parse PDF: {e}") from e

    if not any(p.strip() for p in pages):
        raise PDFParseError(
            "No extractable text found — this PDF may be scanned/image-only "
            "and would need OCR, which this pipeline doesn't do yet."
        )

    return pages
