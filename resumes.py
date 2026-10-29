"""Resume uploads: storage on the persistent disk plus the Resume ORM model."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from modules.models import Base

RESUME_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}

try:
    MAX_UPLOAD_BYTES = int(os.getenv("RESUME_MAX_MB", "5")) * 1024 * 1024
except ValueError:
    raise RuntimeError("RESUME_MAX_MB must be an integer")
if MAX_UPLOAD_BYTES <= 0:
    raise RuntimeError("RESUME_MAX_MB must be positive")


class Resume(Base):
    """One resume per user; a new upload replaces the previous row and file."""

    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    content_label = Column(String(10), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


def resume_dir() -> Path:
    return Path(os.getenv("RESUME_DIR", "./data/resumes"))


def ensure_resume_dir() -> None:
    resume_dir().mkdir(parents=True, exist_ok=True)


def resume_path(stored_filename: str) -> Path:
    return resume_dir() / stored_filename


def delete_resume_file(stored_filename: str) -> None:
    resume_path(stored_filename).unlink(missing_ok=True)


def _display_name(raw: str) -> str:
    # Never trust the client filename for storage paths; use it only as a
    # download label. Strip path components and control characters.
    name = Path(raw.replace("\\", "/")).name.strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return (name or "resume")[:150]


def save_resume_upload(user_id: int, upload: UploadFile) -> Resume:
    """Validate and stream an upload to disk. Returns an unattached Resume."""
    if not upload.filename:
        raise HTTPException(status_code=422, detail="A file is required")

    display = _display_name(upload.filename)
    ext = Path(display).suffix.lower().lstrip(".")
    if ext not in RESUME_MIME:
        raise HTTPException(status_code=422, detail="Resume must be a PDF, DOCX, or TXT file")

    ensure_resume_dir()

    # Sniff magic bytes: the declared Content-Type is client-controlled.
    head = upload.file.read(8)
    if not head:
        raise HTTPException(status_code=422, detail="The uploaded file is empty")
    if ext == "pdf" and not head.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File content does not match the .pdf extension")
    if ext == "docx" and not head.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=422, detail="File content does not match the .docx extension")

    stored = f"{user_id}_{uuid.uuid4().hex}.{ext}"
    dest = resume_path(stored)
    total = len(head)
    try:
        with dest.open("wb") as out:
            out.write(head)
            while chunk := upload.file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Resume must be {MAX_UPLOAD_BYTES // (1024 * 1024)} MB or smaller",
                    )
                out.write(chunk)
    except HTTPException:
        delete_resume_file(stored)
        raise
    except OSError:
        delete_resume_file(stored)
        raise HTTPException(status_code=500, detail="Could not store the uploaded file")

    return Resume(
        user_id=user_id,
        original_filename=display,
        stored_filename=stored,
        content_label=ext,
        size_bytes=total,
    )
