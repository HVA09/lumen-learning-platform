"""Compatibility tests for the legacy quiz-logic import path."""

from app.modules.assessments.domain import quiz_logic as domain_quiz_logic
from app.services import quiz_logic as legacy_quiz_logic


def test_legacy_service_path_reexports_the_domain_public_api():
    assert legacy_quiz_logic.__all__ == domain_quiz_logic.__all__
    for name in domain_quiz_logic.__all__:
        assert getattr(legacy_quiz_logic, name) is getattr(domain_quiz_logic, name)
