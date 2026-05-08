"""
QStash cron endpoint.
Triggered by Upstash QStash on the first Monday of every month at 03:00 IST.
Refreshes market intelligence for all active combinations.
"""

import hashlib
import hmac
import json
import asyncio
import structlog
from fastapi import APIRouter, Request, HTTPException
from backend.config import QSTASH_SIGNING_KEY
from backend.storage.redis_client import redis
from ingestion.pipeline import run_ingestion_for_combo

router = APIRouter()
logger = structlog.get_logger()

# Combinations that are always active from day one
TIER_1_COMBINATIONS = [
    ("SDE1", "Indian Product Company (Tier 1)", "India"),
    ("SDE1", "Indian Service Company", "India"),
    ("SDE1", "Early Stage Startup", "India"),
    ("SDE2", "Indian Product Company (Tier 1)", "India"),
    ("SDE2", "Indian Service Company", "India"),
    ("SDE2", "Early Stage Startup", "India"),
    ("SDE2", "FAANG / Big Tech", "India"),
    ("SDE2", "FAANG / Big Tech", "USA"),
    ("Senior SDE", "Indian Product Company (Tier 1)", "India"),
    ("Senior SDE", "FAANG / Big Tech", "USA"),
    ("ML Engineer", "Indian Product Company (Tier 1)", "India"),
    ("AI Engineer", "Indian Product Company (Tier 1)", "India"),
    ("Full Stack Engineer", "Indian Product Company (Tier 1)", "India"),
    ("Backend Engineer", "Indian Product Company (Tier 1)", "India"),
    ("Data Engineer", "Indian Product Company (Tier 1)", "India"),
    ("Data Scientist", "Indian Product Company (Tier 1)", "India"),
    ("Data Analyst", "Indian Product Company (Tier 1)", "India"),
    ("Product Manager", "Indian Product Company (Tier 1)", "India"),
    ("DevOps / SRE", "Indian Product Company (Tier 1)", "India"),
    ("VLSI Design Engineer", "Semiconductor / Hardware", "India"),
]


def _verify_qstash_signature(body: bytes, signature: str) -> bool:
    """
    Verify the QStash HMAC-SHA256 signature.
    Unsigned or tampered requests are rejected with 401.
    """
    if not QSTASH_SIGNING_KEY:
        # In development, skip verification
        return True

    expected = hmac.new(
        QSTASH_SIGNING_KEY.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def _get_active_combinations() -> list[tuple[str, str, str]]:
    """
    Get combinations that have had at least 1 analysis in the last 30 days.
    Always includes the Tier 1 pre-defined combinations.
    """
    active = set(TIER_1_COMBINATIONS)

    # Add combinations with recent activity from Redis
    # combo_count:{role}:{company_type}:{market} is incremented on every analysis
    try:
        # Scan for combo_count keys — find active combinations
        cursor = 0
        while True:
            cursor, keys = redis.scan(cursor, match="combo_count:*", count=100)
            for key in keys:
                count = redis.get(key)
                if count and int(count) >= 1:
                    # Parse key: combo_count:{role}:{company_type}:{market}
                    parts = key.replace("combo_count:", "").split(":")
                    if len(parts) == 3:
                        active.add(tuple(parts))
            if cursor == 0:
                break
    except Exception as e:
        logger.warning("combo_scan_failed", error=str(e))

    return list(active)


@router.post("/refresh-market-intel")
async def refresh_market_intel(request: Request):
    """
    QStash cron trigger endpoint.
    Refreshes market intelligence for all active combinations.
    HMAC signature verified — unsigned POST rejected with 401.
    """
    body = await request.body()

    # Verify QStash signature
    signature = request.headers.get("upstash-signature", "")
    if not _verify_qstash_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature.")

    # Check Tavily budget before starting
    from ingestion.tavily_client import deep, general
    deep_remaining = deep.budget_remaining()
    general_remaining = general.budget_remaining()

    if deep_remaining < 50 or general_remaining < 50:
        logger.warning(
            "cron_skipped_budget_low",
            deep_remaining=deep_remaining,
            general_remaining=general_remaining,
        )
        # Fire Discord alert
        _notify_discord(f"⚠️ Cron skipped — Tavily budget low. Deep: {deep_remaining}, General: {general_remaining}")
        return {"status": "skipped", "reason": "tavily_budget_low"}

    # Set cron running flag — frontend shows maintenance banner
    cron_ttl = 3600  # expect cron to finish within 1 hour
    redis.setex("cron:running", cron_ttl, "1")

    combinations = _get_active_combinations()

    logger.info("cron_started", combinations=len(combinations))

    results = []
    errors = []

    for role, company_type, market in combinations:
        try:
            summary = await run_ingestion_for_combo(
                role=role,
                company_type=company_type,
                market=market,
                force_refresh=True,
            )
            results.append({
                "combo": f"{role}/{company_type}/{market}",
                "stored": summary.signals_stored,
                "discarded": summary.signals_discarded,
                "duration": summary.duration_seconds,
            })
            logger.info(
                "combo_refreshed",
                role=role, market=market,
                stored=summary.signals_stored,
            )
            # Small delay between combinations to avoid rate limit spikes
            await asyncio.sleep(2)

        except Exception as e:
            errors.append({"combo": f"{role}/{company_type}/{market}", "error": str(e)})
            logger.error("combo_refresh_failed", role=role, market=market, error=str(e))

    # Clear cron running flag
    redis.delete("cron:running")

    total_stored = sum(r["stored"] for r in results)
    summary_msg = f"✅ Cron complete — {len(results)} combos refreshed, {total_stored} signals stored, {len(errors)} errors"
    _notify_discord(summary_msg)

    logger.info("cron_complete", refreshed=len(results), errors=len(errors), total_stored=total_stored)

    return {
        "status": "complete",
        "refreshed": len(results),
        "errors": len(errors),
        "total_signals_stored": total_stored,
        "results": results,
        "error_details": errors,
    }


def _notify_discord(message: str) -> None:
    """Fire Discord webhook notification. Silent fail."""
    try:
        from backend.config import DISCORD_WEBHOOK_URL
        if not DISCORD_WEBHOOK_URL:
            return
        import httpx
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=5)
    except Exception:
        pass
