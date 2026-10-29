"""
Caching بسيط عبر Redis — لو المكتبة غير مثبّتة أو Redis مو وصول، الدوال ترجع None/تتجاهل
بصمت (يعني بدون caching، مو خطأ) — التطبيق يشتغل صح بأي الحالتين.
"""
import json

from app.logging_config import get_logger

logger = get_logger("cache")

try:
    import redis

    from app.config import settings

    _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    _REDIS_AVAILABLE = True
except ImportError:
    _client = None
    _REDIS_AVAILABLE = False
    logger.info("مكتبة redis غير مثبّتة — الـ caching معطّل، التطبيق يشتغل عادي بدونه")


def cache_get(key: str):
    if not _REDIS_AVAILABLE:
        return None
    try:
        value = _client.get(key)
        return json.loads(value) if value is not None else None
    except Exception:
        return None


def cache_set(key: str, value, ttl_seconds: int) -> None:
    if not _REDIS_AVAILABLE:
        return
    try:
        _client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        logger.warning("تعذر الكتابة بـ Redis — تجاهل بصمت")


def cache_delete(key: str) -> None:
    if not _REDIS_AVAILABLE:
        return
    try:
        _client.delete(key)
    except Exception:
        pass
