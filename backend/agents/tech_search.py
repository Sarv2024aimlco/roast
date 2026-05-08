"""
Real-time technology lookup for agents.
When an agent encounters a tool/technology it needs to evaluate,
it can search for it and get a quick summary.
No API key needed — uses DuckDuckGo directly.
"""

import asyncio
import structlog
from duckduckgo_search import DDGS

logger = structlog.get_logger()


async def lookup_technology(tech_name: str, context: str = "") -> str:
    """
    Look up a technology/tool/framework and return a brief summary.
    Used by TechnicalDepthAgent when it encounters unfamiliar tools.

    Args:
        tech_name: e.g. "Bayesian NBV", "d-vector speaker verification", "SIP call transfer"
        context: e.g. "robotics", "voice AI" — helps narrow the search

    Returns:
        Brief description of what the technology is and what it's used for.
        Empty string if lookup fails.
    """
    query = f"{tech_name} {context} technical explanation what is it used for".strip()

    try:
        results = await asyncio.to_thread(_ddg_search, query)
        if not results:
            return ""

        # Take first 2 results, combine snippets
        snippets = [r.get("body", "") for r in results[:2] if r.get("body")]
        combined = " ".join(snippets)[:500]
        return combined

    except Exception as e:
        logger.warning("tech_lookup_failed", tech=tech_name, error=str(e))
        return ""


def _ddg_search(query: str) -> list[dict]:
    """Synchronous DuckDuckGo search — run via asyncio.to_thread."""
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=3))


async def lookup_multiple(technologies: list[str], context: str = "") -> dict[str, str]:
    """
    Look up multiple technologies simultaneously.
    Returns dict of {tech_name: description}.
    """
    tasks = [lookup_technology(tech, context) for tech in technologies]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        tech: (result if isinstance(result, str) else "")
        for tech, result in zip(technologies, results)
    }
