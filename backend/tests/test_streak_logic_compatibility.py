"""Compatibility tests for the former streak-logic service path."""

import app.modules.learning_progress.domain.streak_logic as domain
import app.services.streak_logic as legacy


def test_legacy_facade_reexports_the_same_public_function():
    assert legacy.__all__ is domain.__all__
    assert legacy.compute_streak is domain.compute_streak
