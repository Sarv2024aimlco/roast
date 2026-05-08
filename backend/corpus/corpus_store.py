"""
Anonymised corpus store.
Stores stripped resume signals after opted-in analyses.
No resume text, no name, no email — only structured metadata.
Used by CompetitivePositioningAgent to calibrate percentile estimates.
"""

import json
from datetime import datetime, timezone
from pydantic import BaseModel
from backend.storage.redis_client import redis

CORPUS_TTL = 90 * 24 * 3600   # 90 days
CORPUS_CALIBRATED_THRESHOLD = 30  # minimum signals for "calibrated" confidence


class AnonymisedSignal(BaseModel):
    role: str
    market: str
    company_type: str
    experience_level: str
    week: str                        # YYYY-WNN format e.g. "2026-W18"
    red_flag_count: int
    high_severity_flag_count: int
    has_github: bool
    github_verified: bool
    has_quantified_bullets: bool
    college_tier_signal: str         # tier1 / tier2 / tier3 / unknown
    yoe_band: str                    # 0-2 / 2-5 / 5-8 / 8+
    estimated_percentile_range: str  # e.g. "20th-30th"
    review_model_used: str           # which model wrote the review


def _corpus_key(role: str, company_type: str, market: str, week: str) -> str:
    return f"corpus:{role}:{company_type}:{market}:{week}"


def _current_week() -> str:
    """Returns current week in YYYY-WNN format."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-W%W")


def store_signal(signal: AnonymisedSignal) -> None:
    """
    Append one anonymised signal to the corpus list for this combination + week.
    Uses Redis list — each key holds a list of JSON-encoded signals.
    """
    key = _corpus_key(
        signal.role, signal.company_type, signal.market, signal.week
    )
    redis.rpush(key, signal.model_dump_json())
    redis.expire(key, CORPUS_TTL)


def get_signals(
    role: str,
    company_type: str,
    market: str,
    weeks: int = 12,
) -> list[dict]:
    """
    Retrieve last `weeks` weeks of signals for a combination.
    Returns list of dicts — used by CompetitivePositioningAgent.
    """
    now = datetime.now(timezone.utc)
    all_signals = []

    for week_offset in range(weeks):
        # Calculate week string for each past week
        from datetime import timedelta
        week_date = now - timedelta(weeks=week_offset)
        week_str = week_date.strftime("%Y-W%W")
        key = _corpus_key(role, company_type, market, week_str)

        raw_list = redis.lrange(key, 0, -1)
        if raw_list:
            for raw in raw_list:
                try:
                    all_signals.append(json.loads(raw))
                except Exception:
                    continue

    return all_signals


def get_corpus_size(role: str, company_type: str, market: str) -> int:
    """Count total signals for a combination across last 12 weeks."""
    return len(get_signals(role, company_type, market, weeks=12))


def build_signal_from_pipeline(
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    red_flag_count: int,
    high_severity_count: int,
    profile_links: dict,
    resume_text: str,
    percentile_range: str,
    review_model: str,
) -> AnonymisedSignal:
    """
    Build an AnonymisedSignal from pipeline outputs.
    Called after pipeline completes if user opted in.
    """
    # Detect quantified bullets — look for numbers in bullet points
    import re
    has_quantified = bool(re.search(r'\d+[%xX]|\d+[KkMmBb]|\d+\s*(ms|s|hrs?|days?|users?|requests?)', resume_text))

    # Detect GitHub
    has_github = bool(profile_links.get("github"))
    github_verified = profile_links.get("github_verified", False)

    # Estimate college tier from common signals in resume text
    text_lower = resume_text.lower()
    if any(c in text_lower for c in ["iit", "nit", "bits", "iisc"]):
        college_tier = "tier1"
    elif any(c in text_lower for c in ["vit", "manipal", "srm", "pec", "dtu", "nsit"]):
        college_tier = "tier2"
    else:
        college_tier = "tier3"

    # YOE band from experience level
    yoe_map = {
        "Student / Fresher": "0-2",
        "Junior": "0-2",
        "Mid-level": "2-5",
        "Senior": "5-8",
        "Staff / Principal": "8+",
    }
    yoe_band = yoe_map.get(experience_level, "0-2")

    return AnonymisedSignal(
        role=role,
        market=market,
        company_type=company_type,
        experience_level=experience_level,
        week=_current_week(),
        red_flag_count=red_flag_count,
        high_severity_flag_count=high_severity_count,
        has_github=has_github,
        github_verified=github_verified,
        has_quantified_bullets=has_quantified,
        college_tier_signal=college_tier,
        yoe_band=yoe_band,
        estimated_percentile_range=percentile_range,
        review_model_used=review_model,
    )
