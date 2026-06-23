import json
import os

try:
    import redis
except Exception:
    redis = None

_redis = None


def get_redis():
    """Return a redis.Redis client or None if REDIS_URL not set or redis lib missing."""
    global _redis
    if _redis is not None:
        return _redis

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url or redis is None:
        return None

    _redis = redis.from_url(redis_url, decode_responses=True)
    return _redis


def set_json(key: str, value, ex: int = 0):
    r = get_redis()
    if not r:
        return False
    try:
        r.set(key, json.dumps(value, default=str), ex=ex)
        return True
    except Exception:
        return False


def get_json(key: str):
    r = get_redis()
    if not r:
        return None
    try:
        v = r.get(key)
        if not v:
            return None
        return json.loads(str(v))
    except Exception:
        return None
