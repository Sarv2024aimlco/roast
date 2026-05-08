import asyncio
import httpx
import structlog
from backend.config import CEREBRAS_API_KEY
from backend.llm.circuit_breaker import cerebras_circuit

logger = structlog.get_logger()

CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "llama-3.3-70b"  # 1M tokens/day free


async def cerebras_chat(
    messages: list[dict],
    max_tokens: int = 1500,
    temperature: float = 0.3,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    Make a Cerebras chat completion.
    OpenAI-compatible endpoint. 1M tokens/day free.
    Returns (response_text, metadata).
    """
    if not CEREBRAS_API_KEY:
        raise RuntimeError("cerebras_not_configured")

    if cerebras_circuit.should_skip():
        raise RuntimeError("cerebras_circuit_open")

    backoff = [2, 4, 8]

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.post(
                    CEREBRAS_URL,
                    headers={
                        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": CEREBRAS_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()

                cerebras_circuit.record_success()

                metadata = {
                    "provider": "cerebras",
                    "model": CEREBRAS_MODEL,
                    "input_tokens": data.get("usage", {}).get("prompt_tokens"),
                    "output_tokens": data.get("usage", {}).get("completion_tokens"),
                }

                return text, metadata

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                logger.warning("cerebras_rate_limit", attempt=attempt, session_id=session_id)
                if attempt < 2:
                    await asyncio.sleep(backoff[attempt])
            else:
                cerebras_circuit.record_failure()
                logger.error("cerebras_error", error=str(e), session_id=session_id)
                if attempt < 2:
                    await asyncio.sleep(backoff[attempt])
                else:
                    raise

    raise RuntimeError("cerebras_all_retries_exhausted")
