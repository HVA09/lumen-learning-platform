"""Compatibility facade for the former service import path.

New code should import quiz logic from app.modules.assessments.domain.
This module intentionally re-exports the same public API for callers that
still use app.services.quiz_logic during the migration.
"""

from app.modules.assessments.domain.quiz_logic import (
    ATTEMPT_RESUME_HOURS as ATTEMPT_RESUME_HOURS,
    GATEWAY_PASS_PERCENTAGE as GATEWAY_PASS_PERCENTAGE,
    GATEWAY_QUESTION_COUNT as GATEWAY_QUESTION_COUNT,
    GATEWAY_RETRY_COOLDOWN_MINUTES as GATEWAY_RETRY_COOLDOWN_MINUTES,
    MASTERY_NEW_SCORE_WEIGHT as MASTERY_NEW_SCORE_WEIGHT,
    PRACTICE_QUESTION_COUNT as PRACTICE_QUESTION_COUNT,
    QUESTION_KINDS as QUESTION_KINDS,
    QUIZ_MODES as QUIZ_MODES,
    TRUE_FALSE_CHOICES as TRUE_FALSE_CHOICES,
    can_resume_attempt as can_resume_attempt,
    coerce_bool as coerce_bool,
    coerce_int as coerce_int,
    compute_score_percentage as compute_score_percentage,
    describe_correct_answer as describe_correct_answer,
    gateway_cooldown_remaining_minutes as gateway_cooldown_remaining_minutes,
    grade_answer as grade_answer,
    is_gateway_pass as is_gateway_pass,
    normalize_correct_answer as normalize_correct_answer,
    normalize_text as normalize_text,
    parse_number as parse_number,
    public_choices as public_choices,
    question_count_for_mode as question_count_for_mode,
    select_question_ids as select_question_ids,
    update_mastery as update_mastery,
    validate_question_definition as validate_question_definition,
)
from app.modules.assessments.domain.quiz_logic import __all__ as __all__
