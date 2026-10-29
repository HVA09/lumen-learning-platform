"""
مسارات رفع الملفات وإدارتها: صور، PDF، Word، Excel، CSV
تُخزَّن الملفات على القرص (مجلد UPLOAD_DIR) والبيانات الوصفية بقاعدة البيانات
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.audit import log_event
from app.models.file_attachment import FileAttachment
from app.models.user import User
from app.schemas.file import FileOut

router = APIRouter(prefix="/files", tags=["Files"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "text/csv",
    "application/vnd.ms-excel",  # بعض المتصفحات ترسل CSV/XLS بهذا النوع
}


def _user_upload_dir(user_id: int) -> Path:
    path = Path(settings.UPLOAD_DIR) / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_owned_file(file_id: int, current_user: User, db: Session) -> FileAttachment:
    file = (
        db.query(FileAttachment)
        .filter(FileAttachment.id == file_id, FileAttachment.user_id == current_user.id)
        .first()
    )
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")
    return file


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="نوع الملف غير مدعوم (مسموح: صور، PDF، Word، Excel، CSV)",
        )

    # اقرأ بحد أقصى بايتًا واحدًا فوق الحد لاكتشاف الحجم الزائد دون تحميل
    # الملف غير المحدود كاملًا إلى الذاكرة.
    max_bytes = max(0, settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"الملف أكبر من الحد المسموح ({settings.MAX_UPLOAD_SIZE_MB} ميجابايت)",
        )

    extension = Path(file.filename or "").suffix
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    destination = _user_upload_dir(current_user.id) / stored_filename
    destination.write_bytes(contents)

    attachment = FileAttachment(
        user_id=current_user.id,
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        size_bytes=len(contents),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    log_event(
        db,
        "file_uploaded",
        f"رفع ملف: {attachment.original_filename} بواسطة {current_user.email}",
        current_user.id,
    )
    return attachment


@router.get("", response_model=list[FileOut])
def list_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(FileAttachment)
        .filter(FileAttachment.user_id == current_user.id)
        .order_by(FileAttachment.created_at.desc())
        .all()
    )


@router.get("/{file_id}")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = _get_owned_file(file_id, current_user, db)
    path = _user_upload_dir(current_user.id) / attachment.stored_filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود على القرص")
    return FileResponse(
        path, media_type=attachment.content_type, filename=attachment.original_filename
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = _get_owned_file(file_id, current_user, db)
    path = _user_upload_dir(current_user.id) / attachment.stored_filename
    path.unlink(missing_ok=True)
    db.delete(attachment)
    db.commit()
    log_event(
        db,
        "file_deleted",
        f"حذف ملف: {attachment.original_filename} بواسطة {current_user.email}",
        current_user.id,
    )
