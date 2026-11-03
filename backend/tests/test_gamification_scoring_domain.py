"""Pure tests for Gamification leaderboard scoring."""

from app.modules.gamification.domain.scoring import ScoreComponents, calculate_score


def test_empty_components_produce_zero_points():
    assert calculate_score(ScoreComponents()) == 0


def test_each_verified_component_uses_its_existing_point_value():
    assert calculate_score(ScoreComponents(gateway_passed_count=2)) == 40
    assert calculate_score(ScoreComponents(mastery_points=13)) == 13
    assert calculate_score(ScoreComponents(passing_assignment_count=3)) == 45
    assert calculate_score(ScoreComponents(reviewed_card_count=4)) == 8


def test_all_components_are_combined_using_existing_rules():
    components = ScoreComponents(
        gateway_passed_count=2,
        mastery_points=15,
        passing_assignment_count=3,
        reviewed_card_count=40,
    )
    assert calculate_score(components) == 150


def test_reviewed_card_points_are_capped_at_twenty_five_cards():
    at_cap = calculate_score(ScoreComponents(reviewed_card_count=25))
    above_cap = calculate_score(ScoreComponents(reviewed_card_count=40))
    assert at_cap == 50
    assert above_cap == at_cap
