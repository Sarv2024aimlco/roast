import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.agents.followup_agent import (
    run_followup_agent, has_used_followup, mark_followup_used
)
from backend.storage.session_store import get_session

router = APIRouter()


class FollowUpRequest(BaseModel):
    session_id: str
    section: str       # which section the question is from
    question: str      # the clicked question text


@router.post("/followup")
async def followup(body: FollowUpRequest):
    # Validate session exists
    session = get_session(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    # Enforce one follow-up per section per session — server-side
    if has_used_followup(body.session_id, body.section):
        raise HTTPException(
            status_code=429,
            detail=f"Follow-up already used for section '{body.section}' in this session."
        )

    # Get resume text and review from session
    resume_text = session.get("resume_text", "")
    role = session.get("role", "")
    market = session.get("market", "")
    company_type = session.get("company_type", "")
    experience_level = session.get("experience_level", "Junior")

    # Get review summary from Redis session store
    review_raw = None
    try:
        from backend.storage.redis_client import redis
        review_raw = redis.get(f"session:{body.session_id}:review")
    except Exception:
        pass

    review_summary = ""
    if review_raw:
        try:
            review_data = json.loads(review_raw)
            # Extract relevant section for context
            review_summary = review_data.get(f"{body.section}_section", "")
            if not review_summary:
                review_summary = review_data.get("whats_hurting_section", "")
        except Exception:
            pass

    # Mark as used BEFORE running — prevents double-click race condition
    mark_followup_used(body.session_id, body.section)

    result = await run_followup_agent(
        question=body.question,
        section=body.section,
        resume_text=resume_text,
        review_summary=review_summary,
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        session_id=body.session_id,
    )

    return {"answer": result.answer, "section": body.section}
