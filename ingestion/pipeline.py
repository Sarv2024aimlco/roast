import asyncio
import time
from dataclasses import dataclass

from ingestion.tavily_client import deep, general
from ingestion.levels_scraper import fetch_levels_salary
from ingestion.extractor import process_raw_text
from ingestion.search import insert_signal, delete_signals_for_combo, count_signals_for_combo
from ingestion.embeddings import embed_all_missing

# ── Semaphores ────────────────────────────────────────────────────────────────
# Limit concurrent API calls to stay within rate limits
# These are module-level so they're shared across all concurrent pipeline runs
_groq_sem = asyncio.Semaphore(5)    # max 5 concurrent classifier calls
_gemini_sem = asyncio.Semaphore(3)  # max 3 concurrent Gemma extraction calls

# ── Query templates ───────────────────────────────────────────────────────────

def _build_queries(role: str, company_type: str, market: str) -> dict:
    """
    Build the 10 queries for a combination.
    Returns dict with 'deep' and 'general' lists.
    """
    year = 2026
    return {
        "deep": [
            f"{role} jobs site:naukri.com {market} {year}",
            f"{role} jobs site:wellfound.com {market} {year}",
            f"{role} salary offer {market} site:reddit.com OR site:teamblind.com",
            f"{role} interview experience {company_type} {market} site:leetcode.com OR site:reddit.com",
            f"{role} compensation {market} site:levels.fyi",
            f"{role} hiring {market} {company_type} {year} site:linkedin.com",
        ],
        "general": [
            f"{role} hiring market {market} {year}",
            f"{company_type} layoffs OR hiring {market} {year}",
            f"{role} resume tips {market} {company_type}",
            f"{market} tech hiring outlook {year}",
        ],
    }


# ── Companies to scrape from Levels.fyi ──────────────────────────────────────

# Map company_type to the companies we scrape from Levels.fyi
COMPANY_TYPE_TO_LEVELS_COMPANIES = {
    "Indian Product Company (Tier 1)": ["Flipkart", "Swiggy", "Razorpay", "Zepto", "PhonePe"],
    "Indian Product Company (Tier 2)": ["Meesho"],
    "FAANG / Big Tech": ["Google", "Microsoft", "Amazon", "Meta", "Apple"],
    "Early Stage Startup": [],   # startups rarely on Levels.fyi
    "Growth Stage Startup": [],
    "Indian Service Company": [],
    "Consulting / IB": [],
    "Semiconductor / Hardware": [],
    "MNC India (Non-FAANG)": [],
}


# ── Result summary ────────────────────────────────────────────────────────────

@dataclass
class IngestionSummary:
    role: str
    company_type: str
    market: str
    signals_stored: int
    signals_discarded: int
    tavily_results_fetched: int
    levels_results_fetched: int
    duration_seconds: float


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def _process_one(
    text: str,
    role: str,
    market: str,
    source: str,
    company_type: str,
) -> bool:
    """
    Classify + extract one raw text, insert into SQLite if valid.
    Returns True if a signal was stored, False if discarded.
    Uses semaphores to limit concurrent API calls.
    """
    async with _groq_sem:
        signal = await process_raw_text(text, role, market)

    if signal is None:
        return False

    # key_insight is what gets stored as content — clean, specific, one sentence
    if not signal.key_insight or len(signal.key_insight) < 20:
        return False

    async with _gemini_sem:
        row_id = insert_signal(
            role=role,
            company_type=company_type,
            market=market,
            source=source,
            signal_type=signal.signal_type,
            content=signal.key_insight,
        )

    return row_id is not None


async def run_ingestion_for_combo(
    role: str,
    company_type: str,
    market: str,
    force_refresh: bool = False,
) -> IngestionSummary:
    """
    Full ingestion pipeline for one combination.

    Steps:
    1. Check if fresh data already exists (skip if not force_refresh)
    2. Delete old signals for this combination
    3. Fire 10 Tavily queries simultaneously
    4. Scrape Levels.fyi for relevant companies
    5. Process all results in parallel (classify + extract + store)
    6. Generate embeddings for all new rows
    7. Return summary
    """
    start = time.time()

    # Step 1 — skip if fresh data exists and not forcing refresh
    if not force_refresh:
        existing = count_signals_for_combo(role, company_type, market)
        if existing >= 5:
            return IngestionSummary(
                role=role, company_type=company_type, market=market,
                signals_stored=existing, signals_discarded=0,
                tavily_results_fetched=0, levels_results_fetched=0,
                duration_seconds=0.0,
            )

    # Step 2 — fire all 10 Tavily queries simultaneously BEFORE deleting
    # We only delete old signals after confirming we have new data
    # If Tavily is down, old signals stay intact
    queries = _build_queries(role, company_type, market)

    deep_tasks = [deep.search(q, max_results=5) for q in queries["deep"]]
    general_tasks = [general.search(q, max_results=5) for q in queries["general"]]

    deep_results, general_results = await asyncio.gather(
        asyncio.gather(*deep_tasks, return_exceptions=True),
        asyncio.gather(*general_tasks, return_exceptions=True),
    )

    # Flatten results — each query returns a list of results
    raw_texts: list[tuple[str, str]] = []  # (text, source_name)

    for result_list in deep_results:
        if isinstance(result_list, Exception):
            continue
        for item in result_list:
            content = item.get("content", "").strip()
            url = item.get("url", "")
            if content and len(content) > 100:
                source = _source_from_url(url)
                raw_texts.append((content, source))

    for result_list in general_results:
        if isinstance(result_list, Exception):
            continue
        for item in result_list:
            content = item.get("content", "").strip()
            if content and len(content) > 100:
                raw_texts.append((content, "tavily_general"))

    # Safety check — if Tavily returned almost nothing, abort
    # Keep old signals rather than replacing with empty data
    if len(raw_texts) < 3:
        return IngestionSummary(
            role=role, company_type=company_type, market=market,
            signals_stored=0, signals_discarded=0,
            tavily_results_fetched=len(raw_texts), levels_results_fetched=0,
            duration_seconds=round(time.time() - start, 2),
        )

    # Step 3 — NOW safe to delete old signals (we have new data coming)
    delete_signals_for_combo(role, company_type, market)

    tavily_count = len(raw_texts)

    # Step 4 — scrape Levels.fyi for relevant companies
    companies = COMPANY_TYPE_TO_LEVELS_COMPANIES.get(company_type, [])
    levels_texts: list[tuple[str, str]] = []

    if companies:
        levels_tasks = [fetch_levels_salary(company, role) for company in companies]
        levels_results = await asyncio.gather(*levels_tasks, return_exceptions=True)

        for result in levels_results:
            if isinstance(result, Exception) or not result:
                continue
            raw_text = result.get("raw_text", "").strip()
            if raw_text and len(raw_text) > 100:
                levels_texts.append((raw_text, "levels_fyi"))

    levels_count = len(levels_texts)
    all_texts = raw_texts + levels_texts

    # Step 5 — process all texts in parallel
    process_tasks = [
        _process_one(text, role, market, source, company_type)
        for text, source in all_texts
    ]

    results = await asyncio.gather(*process_tasks, return_exceptions=True)

    stored = sum(1 for r in results if r is True)
    discarded = len(results) - stored

    # Step 6 — generate embeddings for all new rows
    if stored > 0:
        embed_all_missing()

    duration = time.time() - start

    return IngestionSummary(
        role=role,
        company_type=company_type,
        market=market,
        signals_stored=stored,
        signals_discarded=discarded,
        tavily_results_fetched=tavily_count,
        levels_results_fetched=levels_count,
        duration_seconds=round(duration, 2),
    )


def _source_from_url(url: str) -> str:
    """Derive a clean source name from a URL."""
    url_lower = url.lower()
    if "naukri.com" in url_lower:
        return "naukri"
    if "wellfound.com" in url_lower or "angel.co" in url_lower:
        return "wellfound"
    if "reddit.com" in url_lower:
        return "reddit"
    if "leetcode.com" in url_lower:
        return "leetcode"
    if "linkedin.com" in url_lower:
        return "linkedin"
    if "teamblind.com" in url_lower or "blind.com" in url_lower:
        return "blind"
    if "levels.fyi" in url_lower:
        return "levels_fyi"
    return "tavily_deep"
