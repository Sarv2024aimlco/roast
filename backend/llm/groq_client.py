import asyncio
from typing import Any
import structlog
from groq import AsyncGroq, RateLimitError, APIStatusError
from backend.config import GROQ_API_KEYS
from backend.storage.redis_client import redis
from backend.llm.circuit_breaker import groq_circuit

logger = structlog.get_logger()

# Parse comma-separated keys into a pool
_keys = [k.strip() for k in GROQ_API_KEYS.split(",") if k.strip()]
_call_count = 0  # round-robin counter
_call_lock = asyncio.Lock()

# RPD limits per model — tracked server-side since Groq doesn't expose RPD in headers
RPD_LIMITS = {
    "meta-llama/llama-4-scout-17b-16e-instruct": 1000,
    "llama-3.3-70b-versatile": 1000,
    "qwen/qwen3-32b": 1000,
    "llama-3.1-8b-instant": 14400,
}

# Proactive fallback threshold — switch before hitting the wall
RPM_FALLBACK_THRESHOLD = 50


async def _get_client() -> tuple[AsyncGroq, int]:
    """Round-robin across keys on every call — distributes load upfront."""
    global _call_count
    async with _call_lock:
        idx = _call_count % len(_keys)
        _call_count += 1
    return AsyncGroq(api_key=_keys[idx]), idx


def _rotate(current_idx: int) -> int:
    """Return next key index after a 429."""
    return (current_idx + 1) % len(_keys)


def _rpd_key(model: str, key_index: int) -> str:
    """Redis key for tracking daily request count per model per key."""
    return f"groq:rpd:{model}:{key_index}"


def _check_rpd(model: str) -> bool:
    """
    Returns True if we still have RPD budget for this model.
    Checks all keys — if any key has budget, returns True.
    """
    limit = RPD_LIMITS.get(model, 1000)
    for i in range(len(_keys)):
        count = redis.get(_rpd_key(model, i))
        used = int(count) if count else 0
        if used < limit:
            return True
    return False


def _increment_rpd(model: str, key_idx: int = 0) -> None:
    """Increment RPD counter for given key. Resets at midnight UTC via TTL."""
    key = _rpd_key(model, key_idx)
    count = redis.incr(key)
    if count == 1:
        # First call today — set TTL to expire at midnight UTC
        import time
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        ttl = int((midnight - now).total_seconds())
        redis.expire(key, ttl)


async def groq_chat(
    messages: list[dict],
    model: str = "llama-3.1-8b-instant",
    max_tokens: int = 1000,
    temperature: float = 0.1,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    Make a Groq chat completion with:
    - Circuit breaker check
    - RPD budget check
    - Key rotation on 429
    - Proactive fallback on low RPM remaining
    - RPD tracking in Redis

    Returns (response_text, metadata) where metadata includes model used,
    tokens consumed, and whether fallback was triggered.
    """
    if groq_circuit.should_skip():
        raise RuntimeError("groq_circuit_open")

    if not _check_rpd(model):
        raise RuntimeError(f"groq_rpd_exhausted:{model}")

    backoff = [2, 4, 8]
    client, key_idx = await _get_client()  # round-robin pick

    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            text = response.choices[0].message.content.strip()

            # qwen3 thinking mode outputs <think>...</think> before JSON
            # If </think> is present, take everything after it
            # If only <think> is present (truncated), strip from start to first }
            if "</think>" in text:
                text = text[text.index("</think>") + len("</think>"):].strip()
            elif text.startswith("<think>"):
                # thinking block got truncated by max_tokens — no JSON was produced
                # raise so the retry/fallback chain kicks in
                raise RuntimeError("qwen3_thinking_truncated")

            # Track RPD
            _increment_rpd(model, key_idx)

            # Check RPM remaining from headers — proactive fallback
            remaining = None
            if hasattr(response, "headers"):
                remaining_str = response.headers.get("x-ratelimit-remaining-requests")
                if remaining_str:
                    remaining = int(remaining_str)
                    redis.set(f"groq:rpm_remaining:{model}", remaining, ex=60)

            groq_circuit.record_success()

            metadata = {
                "provider": "groq",
                "model": model,
                "key_index": key_idx,
                "rpm_remaining": remaining,
                "input_tokens": response.usage.prompt_tokens if response.usage else None,
                "output_tokens": response.usage.completion_tokens if response.usage else None,
            }

            # Proactive fallback warning — log but don't switch here
            # The caller (provider router) decides whether to switch
            if remaining is not None and remaining < RPM_FALLBACK_THRESHOLD:
                logger.warning(
                    "groq_rpm_low",
                    model=model,
                    remaining=remaining,
                    session_id=session_id,
                )

            return text, metadata

        except RateLimitError:
            logger.warning("groq_rate_limit", model=model, attempt=attempt, session_id=session_id)
            key_idx = _rotate(key_idx)
            client = AsyncGroq(api_key=_keys[key_idx])
            if attempt < 2:
                await asyncio.sleep(backoff[attempt])

        except APIStatusError as e:
            groq_circuit.record_failure()
            logger.error("groq_api_error", error=str(e), model=model, session_id=session_id)
            if attempt < 2:
                await asyncio.sleep(backoff[attempt])
            else:
                raise

        except Exception as e:
            groq_circuit.record_failure()
            logger.error("groq_unexpected_error", error=str(e), session_id=session_id)
            raise

    raise RuntimeError("groq_all_retries_exhausted")
