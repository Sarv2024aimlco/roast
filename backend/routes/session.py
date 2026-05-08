from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.storage.session_store import create_session, get_session as redis_get_session

router = APIRouter()


class SessionInitRequest(BaseModel):
    role: str
    market: str
    company_type: str
    experience_level: str = "Junior"


class SessionInitResponse(BaseModel):
    session_id: str
    message: str


@router.post("/session-init", response_model=SessionInitResponse)
def session_init(body: SessionInitRequest):
    session = create_session(body.role, body.market, body.company_type, body.experience_level)
    return SessionInitResponse(
        session_id=session["session_id"],
        message="Session created. You may now upload your resume.",
    )


@router.get("/session/{session_id}")
def get_session_route(session_id: str):
    session = redis_get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
