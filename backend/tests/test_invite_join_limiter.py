import uuid

import pytest
import redis

from app.services import invite_join_limiter as limiter
from app.services.invite_join_limiter import InviteJoinRateLimitUnavailable


class MemoryRedis:
    """Small deterministic stand-in for the Redis EVAL contract used by the service."""

    def __init__(self):
        self.counts = {}

    def eval(self, script, numkeys, *args):
        assert numkeys == 1
        key = args[0]
        current = self.counts.get(key, 0)

        if script == limiter._RESERVE_SCRIPT:
            maximum, window = int(args[1]), int(args[2])
            if current >= maximum:
                return [0, window]
            self.counts[key] = current + 1
            return [1, window]

        if script == limiter._RELEASE_SCRIPT:
            if current <= 1:
                self.counts.pop(key, None)
            else:
                self.counts[key] = current - 1
            return 1

        raise AssertionError("Unexpected Redis script")


def test_reservation_blocks_after_eight_failed_attempts(monkeypatch):
    store = MemoryRedis()
    monkeypatch.setattr(limiter, "_redis_client", store)

    for _ in range(limiter.MAX_FAILED_JOIN_ATTEMPTS):
        assert limiter.reserve_invite_join_attempt(101) == 0

    assert limiter.reserve_invite_join_attempt(101) == limiter.WINDOW_SECONDS
    assert limiter.reserve_invite_join_attempt(202) == 0


def test_valid_code_release_frees_one_reserved_attempt(monkeypatch):
    store = MemoryRedis()
    monkeypatch.setattr(limiter, "_redis_client", store)

    for _ in range(limiter.MAX_FAILED_JOIN_ATTEMPTS):
        assert limiter.reserve_invite_join_attempt(303) == 0

    assert limiter.reserve_invite_join_attempt(303) > 0
    limiter.release_invite_join_attempt(303)
    assert limiter.reserve_invite_join_attempt(303) == 0


def test_redis_error_fails_closed(monkeypatch):
    class BrokenRedis:
        def eval(self, *_args):
            raise redis.exceptions.ConnectionError("Redis unavailable")

    monkeypatch.setattr(limiter, "_redis_client", BrokenRedis())

    with pytest.raises(InviteJoinRateLimitUnavailable):
        limiter.reserve_invite_join_attempt(404)


def test_redis_release_error_does_not_hide_successful_join(monkeypatch):
    class BrokenRedis:
        def eval(self, *_args):
            raise redis.exceptions.ConnectionError("Redis unavailable")

    monkeypatch.setattr(limiter, "_redis_client", BrokenRedis())
    limiter.release_invite_join_attempt(505)


def test_lua_rate_limit_scripts_with_test_redis_when_available(monkeypatch):
    client = redis.Redis.from_url(
        limiter.settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        client.ping()
    except redis.exceptions.RedisError:
        pytest.skip("A test Redis service is not available")

    test_prefix = f"test:invite-join:{uuid.uuid4().hex}:"
    monkeypatch.setattr(limiter, "_KEY_PREFIX", test_prefix)
    monkeypatch.setattr(limiter, "_redis_client", client)
    user_id = 606

    try:
        for _ in range(limiter.MAX_FAILED_JOIN_ATTEMPTS):
            assert limiter.reserve_invite_join_attempt(user_id) == 0

        retry_after = limiter.reserve_invite_join_attempt(user_id)
        assert 0 < retry_after <= limiter.WINDOW_SECONDS

        limiter.release_invite_join_attempt(user_id)
        assert limiter.reserve_invite_join_attempt(user_id) == 0
    finally:
        client.delete(f"{test_prefix}{user_id}")
