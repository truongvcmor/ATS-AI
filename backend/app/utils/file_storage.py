import os
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def validate_cv_file(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.ALLOWED_CV_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(settings.ALLOWED_CV_EXTENSIONS)}",
        )
    return ext


def save_upload(file_bytes: bytes, original_name: str, ext: str) -> str:
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size of {settings.MAX_UPLOAD_SIZE} bytes",
        )
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}{ext}"
    full_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    with open(full_path, "wb") as f:
        f.write(file_bytes)
    return full_path
