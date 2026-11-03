"""Compatibility facade for the former service import path.

New code should import quiz logic from app.modules.assessments.domain.
This module intentionally re-exports the same public API for callers that
still use app.services.quiz_logic during the migration.
"""

from app.modules.assessments.domain.quiz_logic import (
    ATTEMPT_RESUME_HOURS,
    GATEWAY_PASS_PERCENTAGE,
    GATEWAY_QUESTION_COUNT,
    GATEWAY_RETRY_COOLDOWN_MINUTES,
    MASTERY_NEW_SCORE_WEIGHT,
    PRACTICE_QUESTION_COUNT,
    QUESTION_KINDS,
    QUIZ_MODES,
    TRUE_FALSE_CHOICES,
    can_resume_attempt,
    coerce_bool,
    coerce_int,
    compute_score_percentage,
    describe_correct_answer,
    gateway_cooldown_remaining_minutes,
    grade_answer,
    is_gateway_pass,
    normalize_correct_answer,
    normalize_text,
    parse_number,
    public_choices,
    question_count_for_mode,
    select_question_ids,
    update_mastery,
    validate_question_definition,
)
from app.modules.assessments.domain.quiz_logic import __all__
