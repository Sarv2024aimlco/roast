"""
Langfuse observability wrapper — v4 compatible.
Uses Langfuse v4 API: start_observation (as_type='generation') + create_score.
All calls are fire-and-forget: if Langfuse is down, nothing breaks.
"""

import structlog

logger = structlog.get_logger()

_initialized = False
_langfuse = None


def _init() -> bool:
    """Lazy-init Langfuse. Returns True if successfully initialized."""
    global _initialized, _langfuse
    if _initialized:
        return _langfuse is not None

    try:
        from langfuse import Langfuse
        from backend.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

        if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
            _initialized = True
            return False

        _langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        _initialized = True
        logger.info("langfuse_initialized", host=LANGFUSE_HOST)
        return True

    except Exception as e:
        logger.warning("langfuse_init_failed", error=str(e))
        _initialized = True
        return False


def trace_llm_call(
    session_id: str,
    agent_name: str,
    model: str,
    provider: str,
    messages: list[dict],
    response_text: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    latency_ms: float | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Send a single LLM call trace to Langfuse v4.
    Completely silent on failure — never raises.
    """
    try:
        if not _init():
            return

        system_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")

        usage = {}
        if input_tokens:
            usage["input"] = input_tokens
        if output_tokens:
            usage["output"] = output_tokens

        _langfuse.start_observation(
            name=agent_name,
            as_type="generation",
            input={"system": system_msg[:500], "user": user_msg[:1000]},
            output=response_text[:2000],
            model=model,
            model_parameters={"provider": provider},
            usage_details=usage if usage else None,
            metadata={
                "session_id": session_id,
                "latency_ms": latency_ms,
                **(metadata or {}),
            },
        )
        _langfuse.flush()

    except Exception as e:
        logger.debug("langfuse_trace_failed", error=str(e), agent=agent_name)


def trace_feedback(session_id: str, useful: bool) -> None:
    """Link user feedback (👍/👎) to the session trace."""
    try:
        if not _init():
            return

        _langfuse.create_score(
            name="user_feedback",
            value=1.0 if useful else 0.0,
            comment="thumbs_up" if useful else "thumbs_down",
        )

    except Exception as e:
        logger.debug("langfuse_feedback_failed", error=str(e))
