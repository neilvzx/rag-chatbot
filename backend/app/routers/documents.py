import os
import uuid
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.services.pdf_parser import extract_pages, PDFParseError
from app.services.chunking import chunk_document
from app.services import vector_store

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    os.makedirs(settings.upload_dir, exist_ok=True)
    doc_id = uuid.uuid4()
    saved_path = os.path.join(settings.upload_dir, f"{doc_id}.pdf")

    with open(saved_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    size_mb = os.path.getsize(saved_path) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        os.remove(saved_path)
        raise HTTPException(400, f"File exceeds {settings.max_upload_mb}MB limit")

    document = Document(
        id=doc_id,
        owner_id=current_user.id,
        filename=file.filename,
        file_path=saved_path,
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        pages = extract_pages(saved_path)
        chunks = chunk_document(pages)
        num_stored = vector_store.add_chunks(
            document_id=str(doc_id),
            owner_id=str(current_user.id),
            filename=file.filename,
            chunks=chunks,
        )

        document.status = DocumentStatus.READY
        document.num_pages = len(pages)
        document.num_chunks = num_stored
        db.commit()

    except PDFParseError as e:
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        db.commit()
        raise HTTPException(422, str(e))
    except Exception as e:
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        db.commit()
        raise HTTPException(500, f"Ingestion failed: {e}")

    return {
        "id": str(document.id),
        "filename": document.filename,
        "status": document.status,
        "num_pages": document.num_pages,
        "num_chunks": document.num_chunks,
    }


@router.get("/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "num_pages": doc.num_pages,
        "num_chunks": doc.num_chunks,
        "error_message": doc.error_message,
    }
