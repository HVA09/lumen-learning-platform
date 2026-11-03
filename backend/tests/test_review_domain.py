"""Pure tests for SM-2+ state transitions (no ORM or database)."""

from datetime import datetime, timedelta, timezone

from app.modules.review.domain.sm2 import (
    CardState,
    LEECH_THRESHOLD,
    MAX_EASE_FACTOR,
    MIN_EASE_FACTOR,
    ReviewState,
    transition_review,
)


def _state(
    *,
    state: CardState = CardState.new,
    ease_factor: float = 2.5,
    interval_days: int = 0,
    repetitions: int = 0,
    lapses: int = 0,
    is_leech: bool = False,
) -> ReviewState:
    return ReviewState(
        state=state,
        ease_factor=ease_factor,
        interval_days=interval_days,
        repetitions=repetitions,
        lapses=lapses,
        is_leech=is_leech,
    )


def test_good_reviews_follow_learning_steps_then_graduate():
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    initial = _state()

    first = transition_review(initial, "good", now)
    second = transition_review(first.next_state, "good", now)
    third = transition_review(second.next_state, "good", now)

    assert first.next_state.state is CardState.learning
    assert first.next_state.interval_days == 1
    assert second.next_state.state is CardState.learning
    assert second.next_state.interval_days == 3
    assert third.next_state.state is CardState.review
    assert third.next_state.repetitions == 3
    assert initial == _state()
    assert third.due_at == now + timedelta(days=8)


def test_again_moves_review_card_to_relearning_and_resets_repetitions():
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    current = _state(
        state=CardState.review,
        ease_factor=2.5,
        interval_days=10,
        repetitions=7,
        lapses=2,
    )

    result = transition_review(current, "again", now)

    assert result.next_state.state is CardState.relearning
    assert result.next_state.interval_days == 1
    assert result.next_state.repetitions == 0
    assert result.next_state.lapses == 3
    assert result.next_state.ease_factor == 2.3
    assert result.due_at == now + timedelta(days=1)
    assert current.state is CardState.review
    assert current.repetitions == 7


def test_again_from_learning_returns_to_learning():
    current = _state(state=CardState.learning, repetitions=1, interval_days=1)
    result = transition_review(current, "again")
    assert result.next_state.state is CardState.learning
    assert result.next_state.repetitions == 0
    assert result.next_state.interval_days == 1


def test_easy_grade_increases_ease_and_uses_easy_interval_bonus():
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    current = _state(state=CardState.review, interval_days=5, repetitions=3)

    result = transition_review(current, "easy", now)

    assert result.next_state.state is CardState.review
    assert result.next_state.ease_factor == 2.65
    assert result.next_state.interval_days == 16
    assert result.due_at == now + timedelta(days=16)


def test_again_respects_minimum_ease_factor_and_leech_threshold():
    current = _state(
        state=CardState.review,
        ease_factor=MIN_EASE_FACTOR,
        lapses=LEECH_THRESHOLD - 1,
    )

    result = transition_review(current, "again")

    assert result.next_state.ease_factor == MIN_EASE_FACTOR
    assert result.next_state.lapses == LEECH_THRESHOLD
    assert result.next_state.is_leech is True


def test_easy_grade_respects_maximum_ease_factor():
    current = _state(state=CardState.review, ease_factor=MAX_EASE_FACTOR)
    result = transition_review(current, "easy")
    assert result.next_state.ease_factor == MAX_EASE_FACTOR


def test_leech_flag_remains_set_after_subsequent_success():
    current = _state(state=CardState.review, lapses=LEECH_THRESHOLD, is_leech=True)
    result = transition_review(current, "good")
    assert result.next_state.is_leech is True


def test_transition_uses_utc_now_when_not_supplied():
    result = transition_review(_state(), "good")
    assert result.due_at.tzinfo is not None
