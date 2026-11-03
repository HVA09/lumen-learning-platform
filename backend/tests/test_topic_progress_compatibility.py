"""Compatibility tests for the former learning-path service rule exports."""

import app.modules.learning_progress.domain.topic_progress as domain
import app.services.learning_path as legacy


def test_legacy_service_reexports_the_same_topic_progress_rules():
    assert set(domain.__all__).issubset(legacy.__all__)
    for name in domain.__all__:
        assert getattr(legacy, name) is getattr(domain, name)
