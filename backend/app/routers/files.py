"""
مسارات رفع الملفات وإدارتها: صور، PDF، Word، Excel، CSV
تُخزَّن الملفات على القرص (مجلد UPLOAD_DIR) والبيانات الوصفية بقاعدة البيانات
"""
import codecs
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.audit import log_event
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
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
    "application/vnd.ms-excel",  # CSV أو XLS قديم
}


def _user_upload_dir(user_id: int) -> Path:
    path = Path(settings.UPLOAD_DIR) / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_owned_file(file_id: int, current_user: User, db: Session) -> FileAttachment:
    attachment = (
        db.query(FileAttachment)
        .filter(FileAttachment.id == file_id, FileAttachment.user_id == current_user.id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")
    return attachment


def _is_utf8_text_file(path: Path) -> bool:
    """Validate CSV as UTF-8 text without loading the entire file into memory."""
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    try:
        with path.open("rb") as source:
            while chunk := source.read(64 * 1024):
                if b"\x00" in chunk:
                    return False
                decoder.decode(chunk, final=False)
            decoder.decode(b"", final=True)
    except (OSError, UnicodeDecodeError):
        return False
    return True


def _matches_file_signature(path: Path, content_type: str, extension: str) -> bool:
    """Check extension and file signature; never trust the browser MIME type alone."""
    try:
        with path.open("rb") as source:
            header = source.read(16)
    except OSError:
        return False

    ext = extension.lower()
    if content_type == "image/jpeg":
        return ext in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return ext == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/gif":
        return ext == ".gif" and header[:6] in {b"GIF87a", b"GIF89a"}
    if content_type == "image/webp":
        return ext == ".webp" and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    if content_type == "application/pdf":
        return ext == ".pdf" and header.startswith(b"%PDF-")

    if content_type == "text/csv":
        return ext == ".csv" and _is_utf8_text_file(path)

    if content_type == "application/vnd.ms-excel":
        if ext == ".csv":
            return _is_utf8_text_file(path)
        # Legacy .xls files use the OLE Compound File Binary signature.
        return ext == ".xls" and header.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))

    required_member = None
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        if ext != ".docx":
            return False
        required_member = "word/document.xml"
    elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        if ext != ".xlsx":
            return False
        required_member = "xl/workbook.xml"
    else:
        return False

    # DOCX/XLSX are ZIP containers. Check their expected internal document entry,
    # without extracting archive contents to disk.
    if not header.startswith(b"PK"):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            members = set(archive.namelist())
        return "[Content_Types].xml" in members and required_member in members
    except (OSError, zipfile.BadZipFile):
        return False


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

    max_bytes = max(0, settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024
    extension = Path(file.filename or "").suffix[:20].lower()
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    destination = _user_upload_dir(current_user.id) / stored_filename
    size_bytes = 0

    # Stream in bounded chunks; an oversized request never gets loaded all at once.
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(64 * 1024):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"الملف أكبر من الحد المسموح ({settings.MAX_UPLOAD_SIZE_MB} ميجابايت)",
                    )
                output.write(chunk)

        if not _matches_file_signature(destination, file.content_type, extension):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="محتوى الملف أو امتداده لا يطابق نوع الملف المعلن",
            )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    attachment = FileAttachment(
        user_id=current_user.id,
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        size_bytes=size_bytes,
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
