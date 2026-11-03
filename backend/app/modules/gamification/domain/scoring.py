"""Pure Gamification scoring rules, independent of persistence and HTTP."""

from dataclasses import dataclass


POINTS_PER_GATEWAY_PASSED = 20
POINTS_PER_PASSING_ASSIGNMENT = 15
POINTS_PER_TEN_MASTERY_PERCENT = 1
POINTS_PER_REVIEWED_CARD = 2
MAX_REVIEWED_CARDS_FOR_POINTS = 25


@dataclass(frozen=True, slots=True)
class ScoreComponents:
    """Verified, server-aggregated inputs used to calculate a student's score.

    mastery_points is the sum of floor(mastery_percentage / 10) per topic.
    """

    gateway_passed_count: int = 0
    mastery_points: int = 0
    passing_assignment_count: int = 0
    reviewed_card_count: int = 0


def calculate_score(components: ScoreComponents) -> int:
    """Calculate leaderboard points without querying or trusting client data."""
    return int(
        components.gateway_passed_count * POINTS_PER_GATEWAY_PASSED
        + components.mastery_points * POINTS_PER_TEN_MASTERY_PERCENT
        + components.passing_assignment_count * POINTS_PER_PASSING_ASSIGNMENT
        + min(components.reviewed_card_count, MAX_REVIEWED_CARDS_FOR_POINTS)
        * POINTS_PER_REVIEWED_CARD
    )


__all__ = (
    "POINTS_PER_GATEWAY_PASSED",
    "POINTS_PER_PASSING_ASSIGNMENT",
    "POINTS_PER_TEN_MASTERY_PERCENT",
    "POINTS_PER_REVIEWED_CARD",
    "MAX_REVIEWED_CARDS_FOR_POINTS",
    "ScoreComponents",
    "calculate_score",
)
