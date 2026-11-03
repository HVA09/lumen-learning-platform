"""Compatibility facade for the former streak-logic service path.

New code should import the pure rule from app.modules.learning_progress.domain.
"""

from app.modules.learning_progress.domain.streak_logic import compute_streak
from app.modules.learning_progress.domain.streak_logic import __all__
