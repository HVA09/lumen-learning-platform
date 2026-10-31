"""
مسارات الإشعارات: عرض/تعليم كمقروء عبر REST، واتصال فوري عبر WebSocket
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.auth.cookies import ACCESS_COOKIE_NAME
from app.auth.security import decode_token
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.auth_session import AuthSession
from app.models.notification import Notification
from app.models.user import User
from app.notifications import manager
from app.schemas.notification import NotificationOut

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الإشعار غير موجود")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return {"detail": "تم تعليم كل الإشعارات كمقروءة"}


@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket, db: Session = Depends(get_db)
):
    """Authenticate notification sockets from the HttpOnly access cookie only."""
    origin = websocket.headers.get("origin")
    if origin not in settings.CORS_ORIGINS:
        await websocket.close(code=1008)
        return

    token = websocket.cookies.get(ACCESS_COOKIE_NAME)
    try:
        if not token:
            raise ValueError("missing access cookie")
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("invalid token type")
        user_id = int(payload.get("sub"))
        token_version = payload.get("ver", 0)
        session_id = payload.get("sid")
        if not isinstance(session_id, str):
            raise ValueError("missing server-side session")
    except Exception:
        await websocket.close(code=4001)
        return

    user = db.get(User, user_id)
    auth_session = db.get(AuthSession, session_id)
    now = datetime.now(timezone.utc)
    if (
        user is None
        or not user.is_active
        or token_version != user.token_version
        or auth_session is None
        or auth_session.user_id != user_id
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
