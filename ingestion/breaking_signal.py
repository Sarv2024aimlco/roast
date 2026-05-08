"""
Breaking signal layer.
Captures what happened in tech hiring in the last 7 days.
Keyed per market + role_category + company_type.
Refreshes on first request then cached 24 hours.
"""

import asyncio
import structlog
from backend.storage.redis_client import redis
from ingestion.tavily_client import general

logger = structlog.get_logger()

BREAKING_TTL = 24 * 3600  # 24 hours


def _breaking_key(market: str, role_category: str, company_type: str) -> str:
    return f"breaking:{market.lower()}:{role_category}:{company_type.lower().replace(' ', '_').replace('/', '_')}"


def _role_to_category(role: str) -> str:
    role_lower = role.lower()
    if any(x in role_lower for x in ["sde", "full stack", "backend", "software"]):
        return "sde"
    if any(x in role_lower for x in ["ml", "ai", "machine learning"]):
        return "ai_ml"
    if any(x in role_lower for x in ["data"]):
        return "data"
    if any(x in role_lower for x in ["devops", "sre"]):
        return "devops"
    if any(x in role_lower for x in ["embedded", "vlsi"]):
        return "hardware"
    return "general"


async def get_breaking_signal(
    role: str,
    company_type: str,
    market: str,
    session_id: str = "",
) -> tuple[str, bool]:
    """
    Get breaking signal for this combination.
    Returns (signal_text, is_available).

    Checks Redis cache first (24h TTL).
    On cache miss: fetches from Tavily + synthesises with Gemini Flash Lite.
    If fetch fails: returns empty string, is_available=False.
    Analysis never fails because of a missing breaking signal.
    """
    role_category = _role_to_category(role)
    key = _breaking_key(market, role_category, company_type)

    # Check cache
    cached = redis.get(key)
    if cached:
        return cached, True

    # Cache miss — fetch live
    signal = await _fetch_breaking_signal(role, company_type, market, session_id)

    if signal:
        redis.setex(key, BREAKING_TTL, signal)
        return signal, True

    return "", False


async def _fetch_breaking_signal(
    role: str,
    company_type: str,
    market: str,
    session_id: str = "",
) -> str:
    """
    Fetch and synthesise breaking signal from Tavily + Gemini Flash Lite.
    Returns synthesised text or empty string on failure.
    """
    queries = [
        f"{market} tech hiring news layoffs {role} last 7 days",
        f"{company_type} {market} hiring freeze OR expansion {role} this week",
    ]

    # Fetch from Tavily General
    results = []
    for query in queries:
        try:
            items = await general.search(query, max_results=3)
            for item in items:
                content = item.get("content", "").strip()
                if content and len(content) > 50:
                    results.append(content[:500])
        except Exception:
            continue

    if not results:
        logger.warning("breaking_signal_no_results", role=role, market=market, session_id=session_id)
        return ""

    # Synthesise with Gemini Flash Lite
    combined = "\n\n".join(results[:4])

    prompt = f"""Summarise what happened in tech hiring for {role} roles at {company_type} companies in {market} in the last 7 days.
Be specific. Use company names and numbers if present. 2-3 sentences maximum.
If nothing significant happened, say "No major hiring news this week."

RAW SIGNALS:
{combined}

Summary:"""

    try:
        from backend.llm.gemini_client import gemini_chat, GEMINI_FLASH_LITE
        text, _ = await gemini_chat(
            prompt=prompt,
            model=GEMINI_FLASH_LITE,
            max_tokens=150,
            temperature=0.1,
            session_id=session_id,
        )
        logger.info("breaking_signal_fetched", role=role, market=market, session_id=session_id)
        return text.strip()

    except Exception as e:
        logger.warning("breaking_signal_synthesis_failed", error=str(e), session_id=session_id)
        return ""
