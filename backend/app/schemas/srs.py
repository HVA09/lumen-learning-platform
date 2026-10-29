from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.review_card import CardState


class ReviewCardCreate(BaseModel):
    front_text: str = Field(min_length=1, max_length=2000)
    back_text: str = Field(min_length=1, max_length=2000)
    topic_id: int | None = None


class ReviewCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic_id: int | None
    front_text: str
    back_text: str
    state: CardState
    ease_factor: float
    interval_days: int
    repetitions: int
    lapses: int
    is_leech: bool
    due_at: datetime


class ReviewSubmit(BaseModel):
    grade: Literal["again", "good", "easy"]


class DeckOut(BaseModel):
    topic_id: int
    topic_name_ar: str
    total_cards: int
    added_cards: int  # كم بطاقة من المجموعة أضافها الطالب لبطاقاته


class DeckAddResult(BaseModel):
    added: int
    total: int
