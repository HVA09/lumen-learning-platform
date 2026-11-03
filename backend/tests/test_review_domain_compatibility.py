"""Compatibility and persisted-enum contract tests for the review domain."""

from app.models import CardState as RegistryCardState
from app.models.review_card import CardState as ModelCardState
from app.models.review_card import ReviewCard
from app.modules.review.domain.sm2 import CardState as DomainCardState
from app.schemas.srs import ReviewCardOut
from app.services.spaced_repetition import CardState as ServiceCardState


def test_card_state_enum_is_reexported_from_legacy_paths():
    assert ModelCardState is DomainCardState
    assert RegistryCardState is DomainCardState
    assert ServiceCardState is DomainCardState
    assert ReviewCardOut.model_fields["state"].annotation is DomainCardState


def test_persisted_cardstate_enum_name_and_labels_remain_unchanged():
    enum_type = ReviewCard.__table__.c.state.type
    assert enum_type.name == "cardstate"
    assert enum_type.enums == ["new", "learning", "review", "relearning"]
    assert [member.name for member in DomainCardState] == [
        "new",
        "learning",
        "review",
        "relearning",
    ]
    assert [member.value for member in DomainCardState] == [
        "new",
        "learning",
        "review",
        "relearning",
    ]
