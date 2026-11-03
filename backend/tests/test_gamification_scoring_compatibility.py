"""Compatibility tests for existing service scoring exports."""

import app.modules.gamification.domain.scoring as domain
import app.services.achievements as legacy


def test_legacy_service_reexports_scoring_constants():
    assert legacy.POINTS_PER_GATEWAY_PASSED == domain.POINTS_PER_GATEWAY_PASSED
    assert legacy.POINTS_PER_PASSING_ASSIGNMENT == domain.POINTS_PER_PASSING_ASSIGNMENT
    assert legacy.POINTS_PER_TEN_MASTERY_PERCENT == domain.POINTS_PER_TEN_MASTERY_PERCENT
    assert legacy.POINTS_PER_REVIEWED_CARD == domain.POINTS_PER_REVIEWED_CARD
    assert legacy.MAX_REVIEWED_CARDS_FOR_POINTS == domain.MAX_REVIEWED_CARDS_FOR_POINTS


def test_service_uses_domain_score_calculator():
    assert legacy.calculate_score is domain.calculate_score
    assert legacy.ScoreComponents is domain.ScoreComponents
