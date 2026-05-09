from fastapi import FastAPI

from backend.routes.analyse import router as analyse_router
from backend.routes.session import router as session_router
from backend.routes.followup import router as followup_router
from backend.routes.websocket import router as websocket_router
from backend.routes.cron import router as cron_router
from backend.routes.token_feedback import router as token_feedback_router

app = FastAPI(
    title="ROAST",
    description="Market-aware AI resume critic",
    version="0.1.0",
)

app.include_router(session_router)
app.include_router(analyse_router)
app.include_router(followup_router)
app.include_router(websocket_router)
app.include_router(cron_router)
app.include_router(token_feedback_router)


@app.get("/health")
def health_check():
    from backend.storage.redis_client import redis
    total = redis.get("counter:total_analyses")
    return {
        "status": "ok",
        "service": "roast",
        "total_analyses": int(total) if total else 0,
    }
