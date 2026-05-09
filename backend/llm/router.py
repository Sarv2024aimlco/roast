import asyncio
import structlog
from backend.llm.groq_client import groq_chat
from backend.llm.gemini_client import gemini_chat, GEMINI_FLASH_LITE
from backend.llm.cerebras_client import cerebras_chat
from backend.llm.nvidia_nim_client import nim_chat
from backend.llm.openrouter_client import openrouter_chat

logger = structlog.get_logger()

# ── ReviewAgent fallback chain ────────────────────────────────────────────────
# Tried in order. Groq primary, then NVIDIA NIM
# (40 RPM no daily cap), then Gemma as last resort, then OpenRouter emergency.
REVIEW_MODEL_CHAIN = [
    ("groq",       "meta-llama/llama-4-scout-17b-16e-instruct"),  # 438 tok/s, 2K RPD
    ("groq",       "llama-3.3-70b-versatile"),                    # 345 tok/s, 2K RPD
    ("groq",       "qwen/qwen3-32b"),                             # 243 tok/s, 2K RPD
    ("gemini",     GEMINI_FLASH_LITE),                           # 159 tok/s, 1.5K RPD — thinking disabled
    ("nvidia_nim", None),                                         # 68 tok/s, no daily cap
    ("openrouter", None),                                         # 50 RPD, emergency only
]


async def call_review_agent(
    messages: list[dict],
    max_tokens: int = 3000,
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
    """MarketContextAgent, DIVE distiller, JD parser, FollowUpAgent."""
    return await groq_chat(
        messages=messages, model="llama-3.1-8b-instant",
        max_tokens=max_tokens, temperature=temperature, session_id=session_id,
    )


async def call_red_flag_agent(
    prompt: str,
    max_tokens: int = 2500,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    RedFlagAgent uses llama-3.3-70b-versatile — separate RPM bucket, reliable JSON.
    12K TPM, 1K RPD per key (2K combined). Replaced allam-2-7b which had
    Arabic output, wrong field names, and 4096 context limit issues.
    Falls back to llama-3.1-8b if needed.
    """
    messages = [{"role": "user", "content": prompt}]
    try:
        return await groq_chat(
            messages=messages, model="llama-3.3-70b-versatile",
            max_tokens=max_tokens, temperature=0.1, session_id=session_id,
        )
    except Exception as e:
        logger.warning("red_flag_70b_failed_falling_back", error=str(e), session_id=session_id)
        return await groq_chat(
            messages=messages, model="llama-3.1-8b-instant",
            max_tokens=max_tokens, temperature=0.1, session_id=session_id,
        )


async def call_technical_depth_agent(
    messages: list[dict],
    max_tokens: int = 2000,
    temperature: float = 0.2,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    TechnicalDepthAgent uses gpt-oss-120b — separate RPM bucket, frontier quality.
    gpt-oss-120b: 30 RPM, 1K RPD, 8K TPM per key (16K effective with 2 keys).
    max_tokens=1500 keeps each call under 10% of combined TPM budget.
    Falls back to llama-3.1-8b if needed.
    """
    try:
        return await groq_chat(
            messages=messages, model="openai/gpt-oss-120b",
            max_tokens=max_tokens, temperature=temperature, session_id=session_id,
        )
    except Exception as e:
        logger.warning("tech_depth_gpt_oss_failed_falling_back", error=str(e), session_id=session_id)
        return await groq_chat(
            messages=messages, model="llama-3.1-8b-instant",
            max_tokens=max_tokens, temperature=temperature, session_id=session_id,
        )


async def call_six_second_agent(
    messages: list[dict],
    max_tokens: int = 1000,
    temperature: float = 0.2,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    SixSecondAgent uses gpt-oss-20b on Groq — separate RPM bucket.
    Cerebras key exhausted (402). Falls back to llama-3.1-8b.
    """
    try:
        return await groq_chat(
            messages=messages,
            model="openai/gpt-oss-20b",
            max_tokens=max_tokens,
            temperature=temperature,
            session_id=session_id,
        )
    except Exception as e:
        logger.warning("six_second_gpt_oss_20b_failed_falling_back", error=str(e), session_id=session_id)
        return await groq_chat(
            messages=messages,
            model="llama-3.1-8b-instant",
            max_tokens=max_tokens,
            temperature=temperature,
            session_id=session_id,
        )


async def call_competitive_agent(
    messages: list[dict],
    max_tokens: int = 1500,
    temperature: float = 0.2,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    CompetitiveAgent uses qwen3-32b on Groq — 60 RPM combined, separate bucket.
    max_tokens=1500 to cover ~400 tok thinking block + ~400 tok JSON output.
    Falls back to NIM if Groq exhausted.
    """
    try:
        return await groq_chat(
            messages=messages,
            model="qwen/qwen3-32b",
            max_tokens=max_tokens,
            temperature=temperature,
            session_id=session_id,
        )
    except Exception as e:
        logger.warning("competitive_groq_failed_falling_back", error=str(e), session_id=session_id)
        return await nim_chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            session_id=session_id,
        )


def _messages_to_prompt(messages: list[dict]) -> str:
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
