"""Pure SM-2+ review-state transitions.

This module deliberately has no SQLAlchemy or application-model dependency.
The CardState member names and values are persisted by PostgreSQL as the
existing cardstate enum and must remain stable.
"""

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


class CardState(str, enum.Enum):
    new = "new"
    learning = "learning"
    review = "review"
    relearning = "relearning"


@dataclass(frozen=True, slots=True)
class ReviewState:
    """Persistence-independent state required by the SM-2+ transition."""

    state: CardState
    ease_factor: float
    interval_days: int
    repetitions: int
    lapses: int
    is_leech: bool


@dataclass(frozen=True, slots=True)
class ReviewTransition:
    """New card state plus the next due timestamp."""

    next_state: ReviewState
    due_at: datetime


LEECH_THRESHOLD = 8
GRADUATING_REPETITIONS = 3
LEARNING_STEPS_DAYS = [1, 3]

MIN_EASE_FACTOR = 1.3
MAX_EASE_FACTOR = 3.5
LAPSE_EASE_PENALTY = 0.2
EASY_EASE_BONUS = 0.15
EASY_INTERVAL_BONUS = 1.3
MAX_INTERVAL_DAYS = 365

Grade = str  # "again" | "good" | "easy"


def _next_review_interval(previous_days: int, ease_factor: float, easy: bool) -> int:
    """Grow the interval by at least one day, capped at one year."""
    factor = ease_factor * (EASY_INTERVAL_BONUS if easy else 1.0)
    return min(MAX_INTERVAL_DAYS, max(previous_days + 1, round(previous_days * factor)))


def transition_review(
    current: ReviewState,
    grade: Grade,
    now: datetime | None = None,
) -> ReviewTransition:
    """Return the next immutable review state without mutating ORM or input state."""
    now = now or datetime.now(timezone.utc)

    state = current.state
    ease_factor = current.ease_factor
    interval_days = current.interval_days
    repetitions = current.repetitions
    lapses = current.lapses
    is_leech = current.is_leech

    if grade == "again":
        lapses += 1
        repetitions = 0
        state = CardState.relearning if state == CardState.review else CardState.learning
        interval_days = LEARNING_STEPS_DAYS[0]
        ease_factor = max(MIN_EASE_FACTOR, ease_factor - LAPSE_EASE_PENALTY)
        if lapses >= LEECH_THRESHOLD:
            is_leech = True
    else:
        easy = grade == "easy"
        repetitions += 1

        if state in (CardState.new, CardState.learning, CardState.relearning):
            step_index = repetitions - 1
            if step_index < len(LEARNING_STEPS_DAYS):
                interval_days = LEARNING_STEPS_DAYS[step_index]
                state = CardState.learning
            else:
                state = CardState.review
                interval_days = _next_review_interval(interval_days, ease_factor, easy)
        else:  # already in review — full SM-2 growth
            interval_days = _next_review_interval(interval_days, ease_factor, easy)

        if repetitions >= GRADUATING_REPETITIONS:
            state = CardState.review

        if easy:
            ease_factor = min(MAX_EASE_FACTOR, ease_factor + EASY_EASE_BONUS)

    next_state = ReviewState(
        state=state,
        ease_factor=ease_factor,
        interval_days=interval_days,
        repetitions=repetitions,
        lapses=lapses,
        is_leech=is_leech,
    )
    return ReviewTransition(next_state=next_state, due_at=now + timedelta(days=interval_days))


__all__ = (
    "CardState",
    "ReviewState",
    "ReviewTransition",
    "LEECH_THRESHOLD",
    "GRADUATING_REPETITIONS",
    "LEARNING_STEPS_DAYS",
    "MIN_EASE_FACTOR",
    "MAX_EASE_FACTOR",
    "LAPSE_EASE_PENALTY",
    "EASY_EASE_BONUS",
    "EASY_INTERVAL_BONUS",
    "MAX_INTERVAL_DAYS",
    "Grade",
    "transition_review",
)
