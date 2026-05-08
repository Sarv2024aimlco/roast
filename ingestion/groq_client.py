import asyncio
from groq import AsyncGroq
from backend.config import GROQ_API_KEYS

# Parse comma-separated keys into a list
_keys = [k.strip() for k in GROQ_API_KEYS.split(",") if k.strip()]
_current_index = 0


def _get_client() -> AsyncGroq:
    """Return an AsyncGroq client using the current key."""
    return AsyncGroq(api_key=_keys[_current_index])


def _rotate() -> None:
    """Move to the next key in the pool."""
    global _current_index
    _current_index = (_current_index + 1) % len(_keys)


async def groq_complete(
    system: str,
    user: str,
    model: str = "llama-3.1-8b-instant",
    max_tokens: int = 500,
    retries: int = 3,
) -> str:
    """
    Make a Groq chat completion call with automatic key rotation on 429.
    Returns the response text as a string.
    """
    for attempt in range(retries):
        try:
            client = _get_client()
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.1,  # low temperature = more consistent, less creative
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                _rotate()
                await asyncio.sleep(1)  # brief pause before retry
            elif attempt == retries - 1:
                raise
            else:
                await asyncio.sleep(2)

    return ""
