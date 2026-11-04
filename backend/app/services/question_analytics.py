"""Compatibility facade for the former question analytics service path.

New code should import question analytics from app.modules.assessments.domain.
This module intentionally re-exports the same public API for callers that
still use app.services.question_analytics during the migration.
"""

from app.modules.assessments.domain.question_analytics import (
    EXPECTED_SUCCESS_RANGE as EXPECTED_SUCCESS_RANGE,
    FLAG_CHECK_KEY as FLAG_CHECK_KEY,
    FLAG_EASIER as FLAG_EASIER,
    FLAG_HARDER as FLAG_HARDER,
    FLAG_INSUFFICIENT as FLAG_INSUFFICIENT,
    FLAG_LABELS_AR as FLAG_LABELS_AR,
    FLAG_OK as FLAG_OK,
    MIN_ANSWERS_FOR_ANALYSIS as MIN_ANSWERS_FOR_ANALYSIS,
    classify_question as classify_question,
    most_common_wrong_answer as most_common_wrong_answer,
    sort_for_review as sort_for_review,
    success_rate as success_rate,
)
from app.modules.assessments.domain.question_analytics import __all__ as __all__
