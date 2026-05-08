import json
import time
import uuid 


from backend.storage.redis_client import redis

SESSION_TTL=3600 #1 hour in seconds

def create_session(role: str, market: str, company_type: str, experience_level: str = "Junior") -> dict:
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "role": role,
        "market": market,
        "company_type": company_type,
        "experience_level": experience_level,
        "created_at": int(time.time()),
        "status": "pending"
    }
    #json.dump converts the dictionary to a string,and setex sets them,so redis can store them
    redis.setex(f"session:{session_id}", SESSION_TTL, json.dumps(session))
    return session

def get_session(session_id:str)->dict|None:
    raw=redis.get(f"session:{session_id}")
    if raw is None:
        return None 
    return json.loads(raw)

def update_session(session_id:str, updates:dict)->dict|None:
    session=get_session(session_id)
    if session is None:
        return None
    session.update(updates)
    redis.setex(f"session:{session_id}", SESSION_TTL, json.dumps(session))
    return session