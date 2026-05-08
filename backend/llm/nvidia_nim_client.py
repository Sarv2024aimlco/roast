import asyncio
import httpx
import structlog
from backend.llm.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()

from backend.config import NVIDIA_NIM_API_KEY

NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_NIM_MODEL = "meta/llama-3.3-70b-instruct"

_api_key = NVIDIA_NIM_API_KEY
nim_circuit = CircuitBreaker(name="nvidia_nim")


async def nim_chat(
    messages: list[dict],
    model: str = NVIDIA_NIM_MODEL,
    max_tokens: int = 1500,
    temperature: float = 0.3,
    session_id: str = "",
) -> tuple[str, dict]:
    """
    NVIDIA NIM chat completion.
    40 RPM, no daily token limit, permanently free.
    OpenAI-compatible endpoint.
    """
    if not _api_key:
        raise RuntimeError("nvidia_nim_not_configured")

    if nim_circuit.should_skip():
        raise RuntimeError("nvidia_nim_circuit_open")

    backoff = [2, 4, 8]

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.post(
                    NVIDIA_NIM_URL,
                    headers={
                        "Authorization": f"Bearer {_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()

                nim_circuit.record_success()

                return text, {
                    "provider": "nvidia_nim",
                    "model": model,
                    "input_tokens": data.get("usage", {}).get("prompt_tokens"),
                    "output_tokens": data.get("usage", {}).get("completion_tokens"),
                }

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                logger.warning("nvidia_nim_rate_limit", attempt=attempt, session_id=session_id)
                if attempt < 2:
                    await asyncio.sleep(backoff[attempt])
            else:
                nim_circuit.record_failure()
                logger.error("nvidia_nim_error", error=str(e), session_id=session_id)
                if attempt < 2:
                    await asyncio.sleep(backoff[attempt])
                else:
                    raise

    raise RuntimeError("nvidia_nim_all_retries_exhausted")
