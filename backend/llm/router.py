import asyncio
import structlog
from backend.llm.groq_client import groq_chat
from backend.llm.gemini_client import gemini_chat, GEMMA_4_26B
from backend.llm.cerebras_client import cerebras_chat
from backend.llm.nvidia_nim_client import nim_chat
from backend.llm.openrouter_client import openrouter_chat

logger = structlog.get_logger()

# ── ReviewAgent fallback chain ────────────────────────────────────────────────
# Tried in order. Groq primary, then Cerebras (1M tok/day), then NVIDIA NIM
# (40 RPM no daily cap), then Gemma as last resort, then OpenRouter emergency.
REVIEW_MODEL_CHAIN = [
    ("groq",       "meta-llama/llama-4-scout-17b-16e-instruct"),  # 1K RPD, 30K TPM
    ("groq",       "llama-3.3-70b-versatile"),                    # 1K RPD
    ("groq",       "qwen/qwen3-32b"),                             # 1K RPD, 60 RPM
    ("cerebras",   None),                                         # 1M tok/day free
    ("nvidia_nim", None),                                         # 40 RPM, no daily cap
    ("gemini",     GEMMA_4_26B),                                  # 1.5K RPD, last resort
    ("openrouter", None),                                         # 50 RPD, emergency only
]


async def call_review_agent(
    messages: list[dict],
    max_tokens: int = 1500,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    Try each provider in the fallback chain until one succeeds.
    Returns (response_text, metadata).
    """
    last_error = None

    for provider, model in REVIEW_MODEL_CHAIN:
        try:
            if provider == "groq":
                return await groq_chat(
                    messages=messages, model=model,
                    max_tokens=max_tokens, temperature=0.3,
                    session_id=session_id,
                )
            elif provider == "cerebras":
                return await cerebras_chat(
                    messages=messages, max_tokens=max_tokens,
                    session_id=session_id,
                )
            elif provider == "nvidia_nim":
                return await nim_chat(
                    messages=messages, max_tokens=max_tokens,
                    session_id=session_id,
                )
            elif provider == "gemini":
                prompt = _messages_to_prompt(messages)
                return await gemini_chat(
                    prompt=prompt, model=model,
                    max_tokens=max_tokens, temperature=0.3,
                    session_id=session_id,
                )
            elif provider == "openrouter":
                return await openrouter_chat(
                    messages=messages, max_tokens=max_tokens,
                    session_id=session_id,
                )

        except Exception as e:
            last_error = e
            logger.warning(
                "provider_failed_trying_next",
                provider=provider, model=model,
                error=str(e), session_id=session_id,
            )
            continue

    raise RuntimeError(f"all_providers_failed: {last_error}")


async def call_groq_8b(
    messages: list[dict],
    max_tokens: int = 1000,
    temperature: float = 0.1,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    For all 8B agents: MarketContextAgent, SixSecondAgent,
    CompetitiveAgent, FollowUpAgent, DIVE distiller, JD parser,
    TechnicalDepthAgent, RedFlagAgent (moved from Gemini).
    Uses llama-3.1-8b-instant — 14,400 RPD. Reliable.
    """
    return await groq_chat(
        messages=messages,
        model="llama-3.1-8b-instant",
        max_tokens=max_tokens,
        temperature=temperature,
        session_id=session_id,
    )


async def call_red_flag_agent(
    prompt: str,
    max_tokens: int = 1500,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    RedFlagAgent — moved from Gemini to Groq 8B.
    Gemini free tier has persistent 503 errors at peak times.
    Groq 8B: 14,400 RPD, reliable, no 503s.
    Falls back to Groq 70B if 8B is exhausted.
    """
    messages = [{"role": "user", "content": prompt}]

    # Try Groq 8B first
    try:
        return await groq_chat(
            messages=messages,
            model="llama-3.1-8b-instant",
            max_tokens=max_tokens,
            temperature=0.1,
            session_id=session_id,
        )
    except Exception as e:
        logger.warning("red_flag_8b_failed_trying_70b", error=str(e), session_id=session_id)

    # Fallback to Groq 70B
    try:
        return await groq_chat(
            messages=messages,
            model="llama-3.3-70b-versatile",
            max_tokens=max_tokens,
            temperature=0.1,
            session_id=session_id,
        )
    except Exception as e:
        logger.error("red_flag_all_groq_failed", error=str(e), session_id=session_id)
        raise


def _messages_to_prompt(messages: list[dict]) -> str:
    """Convert OpenAI-style messages to single prompt string for Gemini."""
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"[SYSTEM]\n{content}")
        elif role == "user":
            parts.append(f"[USER]\n{content}")
        elif role == "assistant":
            parts.append(f"[ASSISTANT]\n{content}")
    return "\n\n".join(parts)
