"""
Bullet curation pipeline.
Flags weak bullet + suggested rewrite pairs for manual review.
You review these weekly — approve good ones → they go into example_bullets.json.
Auto-generated examples are prohibited. This is the human-in-the-loop gate.
"""

import json
from pydantic import BaseModel
from backend.storage.redis_client import redis

CURATION_KEY = "curation:candidates"
CURATION_TTL = 30 * 24 * 3600  # 30 days


class BulletCandidate(BaseModel):
    role: str
    company_type: str
    market: str
    weak_bullet: str       # the original weak bullet from the resume
    suggested_rewrite: str # what ReviewAgent suggested
    context: str           # why this was flagged (inference chain excerpt)
    session_id: str        # for tracing — never contains resume text


def flag_bullet_candidate(candidate: BulletCandidate) -> None:
    """
    Add a bullet candidate to the curation queue.
    You review this list weekly and promote approved pairs to example_bullets.json.
    """
    redis.lpush(CURATION_KEY, candidate.model_dump_json())
    redis.expire(CURATION_KEY, CURATION_TTL)

    # Keep queue bounded — max 200 candidates
    redis.ltrim(CURATION_KEY, 0, 199)


def get_candidates(limit: int = 50) -> list[dict]:
    """Fetch pending bullet candidates for manual review."""
    raw_list = redis.lrange(CURATION_KEY, 0, limit - 1)
    candidates = []
    for raw in raw_list:
        try:
            candidates.append(json.loads(raw))
        except Exception:
            continue
    return candidates


def extract_bullet_candidates(
    review_text: str,
    role: str,
    company_type: str,
    market: str,
    session_id: str,
) -> list[BulletCandidate]:
    """
    Parse the review's whats_hurting_section for bullet rewrites.
    Looks for patterns like 'Instead of X, write Y' or 'Rewrite: X → Y'.
    Simple heuristic — not perfect, but catches the obvious cases.
    """
    import re
    candidates = []

    # Pattern: "instead of 'X', write 'Y'"
    pattern1 = re.findall(
        r"instead of ['\"](.{10,150})['\"],?\s+(?:write|try|use)\s+['\"](.{10,150})['\"]",
        review_text,
        re.IGNORECASE,
    )
    for weak, strong in pattern1:
        candidates.append(BulletCandidate(
            role=role,
            company_type=company_type,
            market=market,
            weak_bullet=weak.strip(),
            suggested_rewrite=strong.strip(),
            context="Extracted from review whats_hurting_section",
            session_id=session_id,
        ))

    # Pattern: "X → Y" or "X -> Y"
    pattern2 = re.findall(
        r"['\"](.{10,150})['\"]?\s*[→\->]+\s*['\"](.{10,150})['\"]",
        review_text,
        re.IGNORECASE,
    )
    for weak, strong in pattern2:
        candidates.append(BulletCandidate(
            role=role,
            company_type=company_type,
            market=market,
            weak_bullet=weak.strip(),
            suggested_rewrite=strong.strip(),
            context="Extracted from review rewrite suggestion",
            session_id=session_id,
        ))

    return candidates[:3]  # max 3 candidates per analysis
