"""
Redis-backed protection for repeated classroom invitation-code guesses.

The reservation is counted atomically before looking up a code. A valid code
releases its reservation; an invalid/archived code keeps it until the fixed
window expires. Redis failures fail closed so the endpoint cannot silently
fall back to an unshared per-process counter.
"""
import redis

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("invite_join_limiter")

MAX_FAILED_JOIN_ATTEMPTS = 8
WINDOW_SECONDS = 15 * 60
_KEY_PREFIX = "security:class-invite-join:v1:user:"

_RESERVE_SCRIPT = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current >= tonumber(ARGV[1]) then
    local ttl = redis.call('TTL', KEYS[1])
    if ttl < 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[2])
        ttl = tonumber(ARGV[2])
    end
    return {0, ttl}
end

local next_count = redis.call('INCR', KEYS[1])
if next_count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return {1, redis.call('TTL', KEYS[1])}
"""

_RELEASE_SCRIPT = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current <= 1 then
    redis.call('DEL', KEYS[1])
else
    redis.call('DECR', KEYS[1])
end
return 1
"""

_redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


class InviteJoinRateLimitUnavailable(RuntimeError):
    """Raised when Redis cannot safely enforce the shared join limit."""


def _key_for_user(user_id: int) -> str:
    return f"{_KEY_PREFIX}{int(user_id)}"


def reserve_invite_join_attempt(user_id: int) -> int:
    """Return 0 when allowed, otherwise seconds until retry is allowed."""
    try:
        result = _redis_client.eval(
            _RESERVE_SCRIPT,
            1,
            _key_for_user(user_id),
            MAX_FAILED_JOIN_ATTEMPTS,
            WINDOW_SECONDS,
        )
        allowed, retry_after = int(result[0]), int(result[1])
    except (redis.exceptions.RedisError, TypeError, ValueError, IndexError, KeyError) as exc:
        logger.exception("Redis could not enforce classroom invitation join throttling")
        raise InviteJoinRateLimitUnavailable from exc

    return 0 if allowed == 1 else max(1, retry_after)


def release_invite_join_attempt(user_id: int) -> None:
    """Release the reservation after a valid invitation code is confirmed."""
    try:
        _redis_client.eval(_RELEASE_SCRIPT, 1, _key_for_user(user_id))
    except redis.exceptions.RedisError:
        # The successful join should not be turned into an error. The stale
        # reservation expires automatically at the end of the fixed window.
        logger.warning(
            "Redis could not release a successful classroom invitation attempt",
            exc_info=True,
        )
