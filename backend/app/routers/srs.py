"""
مسارات التكرار المتباعد (SM-2+): إنشاء بطاقات، عرض المستحقة، تقييم مراجعة،
مجموعات بطاقات جاهزة لكل موضوع، وتصدير/استيراد CSV لبطاقات الطالب
"""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.review_card import ReviewCard
from app.models.topic import Topic
from app.models.topic_card import TopicCard
from app.models.user import User
from app.schemas.srs import DeckAddResult, DeckOut, ReviewCardCreate, ReviewCardOut, ReviewSubmit
from app.services.achievements import check_and_award_achievements
from app.services.spaced_repetition import review_card as apply_review
from app.services.study_activity import record_study_activity

router = APIRouter(prefix="/srs", tags=["Spaced Repetition"])

MAX_SRS_CSV_IMPORT_BYTES = 1024 * 1024
MAX_SRS_CSV_IMPORT_ROWS = 500
MAX_SRS_CARD_FIELD_CHARS = 2000


@router.post("/cards", response_model=ReviewCardOut, status_code=status.HTTP_201_CREATED)
def create_card(
    payload: ReviewCardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = ReviewCard(
        user_id=current_user.id,
        topic_id=payload.topic_id,
        front_text=payload.front_text,
        back_text=payload.back_text,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.get("/cards", response_model=list[ReviewCardOut])
def list_cards(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(ReviewCard)
        .filter(ReviewCard.user_id == current_user.id)
        .order_by(ReviewCard.created_at.desc())
        .all()
    )


@router.get("/decks", response_model=list[DeckOut])
def list_decks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """مجموعات البطاقات الجاهزة (واحدة لكل موضوع) — مع عدد اللي أضافه الطالب منها"""
    totals = dict(
        db.query(TopicCard.topic_id, func.count(TopicCard.id)).group_by(TopicCard.topic_id).all()
    )
    if not totals:
        return []

    added = dict(
        db.query(TopicCard.topic_id, func.count(func.distinct(TopicCard.id)))
        .join(
            ReviewCard,
            and_(
                ReviewCard.topic_id == TopicCard.topic_id,
                ReviewCard.front_text == TopicCard.front_text,
                ReviewCard.user_id == current_user.id,
            ),
        )
        .group_by(TopicCard.topic_id)
        .all()
    )
    topics = (
        db.query(Topic)
        .filter(Topic.id.in_(list(totals)))
        .order_by(Topic.subject_id, Topic.order_index)
        .all()
    )
    return [
        DeckOut(
            topic_id=t.id,
            topic_name_ar=t.name_ar,
            total_cards=totals[t.id],
            added_cards=added.get(t.id, 0),
        )
        for t in topics
    ]


@router.post("/decks/{topic_id}/add", response_model=DeckAddResult)
def add_deck_to_my_cards(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ينسخ بطاقات الموضوع الجاهزة لبطاقات الطالب (بدون تكرار لو أضافها قبل) فتدخل جدول المراجعة"""
    if not db.get(Topic, topic_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموضوع غير موجود")

    starter_cards = (
        db.query(TopicCard)
        .filter(TopicCard.topic_id == topic_id)
        .order_by(TopicCard.order_index, TopicCard.id)
        .all()
    )
    if not starter_cards:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="لا توجد بطاقات جاهزة لهذا الموضوع"
        )

    existing_fronts = {
        row[0]
        for row in db.query(ReviewCard.front_text)
        .filter(ReviewCard.user_id == current_user.id, ReviewCard.topic_id == topic_id)
        .all()
    }
    added = 0
    for card in starter_cards:
        if card.front_text in existing_fronts:
            continue
        db.add(
            ReviewCard(
                user_id=current_user.id,
                topic_id=topic_id,
                front_text=card.front_text,
                back_text=card.back_text,
            )
        )
        added += 1
    if added:
        db.commit()
    return DeckAddResult(added=added, total=len(starter_cards))


@router.get("/due", response_model=list[ReviewCardOut])
def get_due_cards(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    return (
        db.query(ReviewCard)
        .filter(ReviewCard.user_id == current_user.id, ReviewCard.due_at <= now)
        .order_by(ReviewCard.due_at)
        .limit(limit)
        .all()
    )


def _get_owned_card(card_id: int, current_user: User, db: Session) -> ReviewCard:
    card = (
        db.query(ReviewCard)
        .filter(ReviewCard.id == card_id, ReviewCard.user_id == current_user.id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="البطاقة غير موجودة")
    return card


@router.post("/cards/{card_id}/review", response_model=ReviewCardOut)
def submit_review(
    card_id: int,
    payload: ReviewSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = _get_owned_card(card_id, current_user, db)
    apply_review(card, payload.grade)
    db.commit()
    db.refresh(card)
    record_study_activity(db, current_user.id)
    check_and_award_achievements(db, current_user.id)
    return card


@router.delete("/cards/{card_id}")
def delete_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = _get_owned_card(card_id, current_user, db)
    db.delete(card)
    db.commit()
    return {"detail": "تم حذف البطاقة"}


@router.get("/export.csv", include_in_schema=False)
def export_cards_csv(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cards = db.query(ReviewCard).filter(ReviewCard.user_id == current_user.id).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["front_text", "back_text", "topic_id"])
    for c in cards:
        writer.writerow([c.front_text, c.back_text, c.topic_id or ""])
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=flashcards.csv"},
    )


@router.post("/import.csv", response_model=list[ReviewCardOut])
async def import_cards_csv(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import a bounded CSV file after validating every row before writing any cards."""
    raw = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        if len(raw) + len(chunk) > MAX_SRS_CSV_IMPORT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="حجم ملف CSV يتجاوز الحد المسموح (1 MiB)",
            )
        raw.extend(chunk)
    await file.close()

    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ملف CSV يجب أن يكون بترميز UTF-8",
        ) from exc

    reader = csv.DictReader(io.StringIO(decoded))
    required = {"front_text", "back_text"}
    fieldnames = reader.fieldnames or []
    if (
        not fieldnames
        or len(fieldnames) != len(set(fieldnames))
        or not required.issubset(set(fieldnames))
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ملف CSV يحتاج أعمدة front_text وback_text بأسماء غير مكررة",
        )

    prepared_cards = []
    topic_ids = set()
    try:
        for row in reader:
            if None in row:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="يوجد صف يحتوي أعمدة إضافية غير موجودة في رأس CSV",
                )

            front = (row.get("front_text") or "").strip()
            back = (row.get("back_text") or "").strip()
            if not front or not back:
                continue

            if (
                len(front) > MAX_SRS_CARD_FIELD_CHARS
                or len(back) > MAX_SRS_CARD_FIELD_CHARS
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="طول وجه البطاقة أو ظهرها يتجاوز 2000 حرف",
                )

            topic_id_raw = (row.get("topic_id") or "").strip()
            topic_id = None
            if topic_id_raw:
                if not topic_id_raw.isdigit() or int(topic_id_raw) <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="topic_id يجب أن يكون رقم موضوع صحيحًا موجبًا",
                    )
                topic_id = int(topic_id_raw)
                topic_ids.add(topic_id)

            prepared_cards.append(
                {
                    "front_text": front,
                    "back_text": back,
                    "topic_id": topic_id,
                }
            )
            if len(prepared_cards) > MAX_SRS_CSV_IMPORT_ROWS:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="ملف CSV يتجاوز الحد الأقصى وهو 500 بطاقة",
                )
    except csv.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="تعذر تحليل ملف CSV",
        ) from exc

    if topic_ids:
        existing_topic_ids = {
            row[0]
            for row in db.query(Topic.id).filter(Topic.id.in_(topic_ids)).all()
        }
        missing_topic_ids = topic_ids - existing_topic_ids
        if missing_topic_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="الملف يحتوي topic_id غير موجود",
            )

    created = [
        ReviewCard(
            user_id=current_user.id,
            topic_id=row["topic_id"],
            front_text=row["front_text"],
            back_text=row["back_text"],
        )
        for row in prepared_cards
    ]
    if created:
        db.add_all(created)
        db.commit()
        for card in created:
            db.refresh(card)
    return created
