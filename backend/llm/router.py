import asyncio
import structlog
from backend.llm.groq_client import groq_chat
from backend.llm.gemini_client import gemini_chat, GEMMA_27B, GEMINI_FLASH_LITE, GEMMA_4_26B
from backend.llm.openrouter_client import openrouter_chat

logger = structlog.get_logger()

# ── ReviewAgent fallback chain ────────────────────────────────────────────────
REVIEW_MODEL_CHAIN = [
    ("groq",       "meta-llama/llama-4-scout-17b-16e-instruct"),  # Primary: 1K RPD, 30K TPM
    ("groq",       "llama-3.3-70b-versatile"),                    # Fallback A: 1K RPD
    ("groq",       "qwen/qwen3-32b"),                             # Fallback B: 1K RPD, 60 RPM
    ("groq",       "openai/gpt-oss-120b"),                        # Fallback C: frontier class, 1K RPD
    ("gemini",     GEMMA_4_26B),                                  # Fallback D: 1.5K RPD, unlimited TPM
    ("openrouter", None),                                         # Last resort: 50 RPD
]


async def call_review_agent(
    messages: list[dict],
    max_tokens: int = 1500,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    Try each provider in the fallback chain until one succeeds.
    Returns (response_text, metadata).
    Raises RuntimeError if all providers fail.
    """
    last_error = None

    for provider, model in REVIEW_MODEL_CHAIN:
        try:
            if provider == "groq":
                return await groq_chat(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.3,
                    session_id=session_id,
                )
            elif provider == "gemini":
                prompt = _messages_to_prompt(messages)
                return await gemini_chat(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.3,
                    session_id=session_id,
                )
            elif provider == "openrouter":
                return await openrouter_chat(
                    messages=messages,
                    max_tokens=max_tokens,
                    session_id=session_id,
                )

        except Exception as e:
            last_error = e
            logger.warning(
                "provider_failed_trying_next",
                provider=provider,
                model=model,
                error=str(e),
                session_id=session_id,
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
    CompetitiveAgent, FollowUpAgent, DIVE distiller, JD parser.
    Uses llama-3.1-8b-instant — 14,400 RPD.
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
    RedFlagAgent uses Gemini 3.1 Flash Lite — strong instruction following,
    500 RPD free. Falls back to Gemma 27B if Flash Lite fails.
    """
    try:
        return await gemini_chat(
            prompt=prompt,
            model=GEMINI_FLASH_LITE,
            max_tokens=max_tokens,
            temperature=0.1,
            session_id=session_id,
        )
    except Exception as e:
        logger.warning("flash_lite_failed_falling_back_to_gemma", error=str(e), session_id=session_id)
        return await gemini_chat(
            prompt=prompt,
            model=GEMMA_27B,
            max_tokens=max_tokens,
            temperature=0.1,
            session_id=session_id,
        )


def _messages_to_prompt(messages: list[dict]) -> str:
    """
    Convert OpenAI-style messages list to a single prompt string for Gemini.
    Gemini takes a single string, not a messages array.
    """
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
