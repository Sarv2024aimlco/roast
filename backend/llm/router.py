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
    """MarketContextAgent, DIVE distiller, JD parser, FollowUpAgent."""
    return await groq_chat(
        messages=messages, model="llama-3.1-8b-instant",
        max_tokens=max_tokens, temperature=temperature, session_id=session_id,
    )


async def call_red_flag_agent(
    prompt: str,
    max_tokens: int = 1500,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    RedFlagAgent uses allam-2-7b — separate RPM bucket from llama-3.1-8b.
    allam-2-7b: 30 RPM, 7K RPD. Good for structured extraction.
    Falls back to llama-3.1-8b if needed.
    """
    messages = [{"role": "user", "content": prompt}]
    try:
        return await groq_chat(
            messages=messages, model="allam-2-7b",
            max_tokens=max_tokens, temperature=0.1, session_id=session_id,
        )
    except Exception as e:
        logger.warning("red_flag_allam_failed_falling_back", error=str(e), session_id=session_id)
        return await groq_chat(
            messages=messages, model="llama-3.1-8b-instant",
            max_tokens=max_tokens, temperature=0.1, session_id=session_id,
        )


async def call_technical_depth_agent(
    messages: list[dict],
    max_tokens: int = 1500,
    temperature: float = 0.2,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    TechnicalDepthAgent uses gpt-oss-120b — separate RPM bucket, frontier quality.
    gpt-oss-120b: 30 RPM, 1K RPD. Best reasoning for technical evaluation.
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
    SixSecondAgent uses Cerebras — spreads load away from Groq.
    Cerebras: 1M tokens/day, 30 RPM, permanently free.
    Falls back to Groq if Cerebras unavailable.
    """
    try:
        return await cerebras_chat(
            messages=messages,
            max_tokens=max_tokens,
            session_id=session_id,
        )
    except Exception as e:
        logger.warning("six_second_cerebras_failed_falling_back", error=str(e), session_id=session_id)
        return await groq_chat(
            messages=messages,
            model="llama-3.1-8b-instant",
            max_tokens=max_tokens,
            temperature=temperature,
            session_id=session_id,
        )


async def call_competitive_agent(
    messages: list[dict],
    max_tokens: int = 1000,
    temperature: float = 0.2,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    CompetitiveAgent uses NVIDIA NIM — spreads load away from Groq.
    NVIDIA NIM: 40 RPM, no daily cap, permanently free.
    Falls back to Groq if NIM unavailable.
    """
    try:
        return await nim_chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            session_id=session_id,
        )
    except Exception as e:
        logger.warning("competitive_nim_failed_falling_back", error=str(e), session_id=session_id)
        return await groq_chat(
            messages=messages,
            model="llama-3.1-8b-instant",
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
