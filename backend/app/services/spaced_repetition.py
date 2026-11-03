"""ORM adapter for the pure SM-2+ review-state transition."""

from datetime import datetime

from app.models.review_card import ReviewCard
from app.modules.review.domain.sm2 import (
    EASY_EASE_BONUS,
    EASY_INTERVAL_BONUS,
    GRADUATING_REPETITIONS,
    LEARNING_STEPS_DAYS,
    LAPSE_EASE_PENALTY,
    LEECH_THRESHOLD,
    MAX_EASE_FACTOR,
    MAX_INTERVAL_DAYS,
    MIN_EASE_FACTOR,
    CardState,
    Grade,
    ReviewState,
    ReviewTransition,
    _next_review_interval,
    transition_review,
)


def review_card(card: ReviewCard, grade: Grade, now: datetime | None = None) -> ReviewCard:
    """Apply one SM-2+ transition to an ORM card in place and return that same card."""
    current = ReviewState(
        state=card.state,
        ease_factor=card.ease_factor,
        interval_days=card.interval_days,
        repetitions=card.repetitions,
        lapses=card.lapses,
        is_leech=card.is_leech,
    )
    result: ReviewTransition = transition_review(current, grade, now=now)
    updated = result.next_state

    card.state = updated.state
    card.ease_factor = updated.ease_factor
    card.interval_days = updated.interval_days
    card.repetitions = updated.repetitions
    card.lapses = updated.lapses
    card.is_leech = updated.is_leech
    card.due_at = result.due_at
    return card


__all__ = (
    "CardState",
    "Grade",
    "LEECH_THRESHOLD",
    "GRADUATING_REPETITIONS",
    "LEARNING_STEPS_DAYS",
    "MIN_EASE_FACTOR",
    "MAX_EASE_FACTOR",
    "LAPSE_EASE_PENALTY",
    "EASY_EASE_BONUS",
    "EASY_INTERVAL_BONUS",
    "MAX_INTERVAL_DAYS",
    "review_card",
)
