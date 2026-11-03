"""Compatibility tests for the former question analytics service path."""

import app.modules.assessments.domain.question_analytics as domain
import app.services.question_analytics as legacy


def test_legacy_facade_reexports_the_same_public_api_objects():
    assert legacy.__all__ is domain.__all__
    for name in domain.__all__:
        assert getattr(legacy, name) is getattr(domain, name)
