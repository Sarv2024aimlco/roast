from datetime import datetime, time
from zoneinfo import ZoneInfo

from backend.storage.redis_client import redis

FREE_ANALYSES_PER_DAY = 2
IST = ZoneInfo("Asia/Kolkata")


def _seconds_until_midnight_ist() -> int:
    """
    Calculate seconds remaining until midnight IST.
    This becomes the TTL for rate limit keys.
    """
    now = datetime.now(IST)
    midnight = datetime.combine(now.date(), time(0, 0, 0), tzinfo=IST)

    # if it's past midnight (shouldn't happen, but safe), go to next midnight
    from datetime import timedelta

    if midnight <= now:
        midnight += timedelta(days=1)

    return int((midnight - now).total_seconds())


def check_and_increment_rate_limit(ip: str) -> dict:
    """
    Check if this IP has analyses remaining today.
    If yes, increment the counter and return allowed=True.
    If no, return allowed=False.

    Returns:
        {
            "allowed": bool,
            "count": int,       # analyses used today
            "remaining": int,   # analyses left today
            "limit": int,       # total daily limit
        }
    """
    key = f"ratelimit:{ip}"

    # INCR atomically increments and returns the new value
    # If the key doesn't exist, Redis creates it at 0 and increments to 1
    count = redis.incr(key)

    if count == 1:
        # First request today — set the TTL to expire at midnight IST
        ttl = _seconds_until_midnight_ist()
        redis.expire(key, ttl)

    allowed = count <= FREE_ANALYSES_PER_DAY
    remaining = max(0, FREE_ANALYSES_PER_DAY - count)

    # If over the limit, undo the increment — don't count blocked requests
    if not allowed:
        redis.decr(key)

    return {
        "allowed": allowed,
        "count": min(count, FREE_ANALYSES_PER_DAY),
        "remaining": remaining,
        "limit": FREE_ANALYSES_PER_DAY,
    }


def get_rate_limit_status(ip: str) -> dict:
    """
    Check current rate limit status without incrementing.
    Used for debugging or preflight checks.
    """
    key = f"ratelimit:{ip}"
    count = redis.get(key)
    count = int(count) if count else 0
    return {
        "count": count,
        "remaining": max(0, FREE_ANALYSES_PER_DAY - count),
        "limit": FREE_ANALYSES_PER_DAY,
    }

