"""Backward-compatible exports for uploaded resume file storage.

Editable legacy resume records remain mapped in modules.models.Resume. Uploaded
files use modules.resumes.Resume and the separate resume_uploads table.
"""
from modules.resumes import (
    RESUME_MIME,
    ResumeUpload as Resume,
    delete_resume_file,
    ensure_resume_dir,
    resume_dir,
    resume_path,
    save_resume_upload,
)

__all__ = [
    "RESUME_MIME",
    "Resume",
    "delete_resume_file",
    "ensure_resume_dir",
    "resume_dir",
    "resume_path",
    "save_resume_upload",
]
