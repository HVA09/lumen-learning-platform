"""Pure topic-progress rules owned by the Learning Progress domain."""

STATUS_LOCKED = "locked"
STATUS_AVAILABLE = "available"
STATUS_IN_PROGRESS = "in_progress"
STATUS_MASTERED = "mastered"


def compute_topic_status(*, gateway_passed: bool, prerequisite_met: bool, has_activity: bool) -> str:
    """Resolve a topic's progress state from verified progress facts."""
    if gateway_passed:
        return STATUS_MASTERED
    if not prerequisite_met:
        return STATUS_LOCKED
    return STATUS_IN_PROGRESS if has_activity else STATUS_AVAILABLE


def pick_recommended_topic(ordered_topics: list[dict]) -> int | None:
    """Prefer the weakest in-progress topic, otherwise the first available topic.

    ordered_topics must already follow curriculum order (subject, then topic).
    """
    in_progress = [topic for topic in ordered_topics if topic["status"] == STATUS_IN_PROGRESS]
    if in_progress:
        # min preserves curriculum order when mastery percentages are equal.
        return min(in_progress, key=lambda topic: topic["mastery_percentage"])["id"]
    for topic in ordered_topics:
        if topic["status"] == STATUS_AVAILABLE:
            return topic["id"]
    return None


__all__ = (
    "STATUS_LOCKED",
    "STATUS_AVAILABLE",
    "STATUS_IN_PROGRESS",
    "STATUS_MASTERED",
    "compute_topic_status",
    "pick_recommended_topic",
)
