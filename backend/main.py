from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

from backend.routes.analyse import router as analyse_router
from backend.routes.session import router as session_router
from backend.routes.followup import router as followup_router
from backend.routes.websocket import router as websocket_router
from backend.routes.cron import router as cron_router
from backend.routes.token_feedback import router as token_feedback_router
from backend.config import ENVIRONMENT, ALLOWED_ORIGINS

app = FastAPI(
    title="ROAST",
    description="Market-aware AI resume critic",
    version="0.1.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True if ALLOWED_ORIGINS != ["*"] else False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(session_router, prefix="/api")
app.include_router(analyse_router, prefix="/api")
app.include_router(followup_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
app.include_router(cron_router)
app.include_router(token_feedback_router, prefix="/api")


@app.get("/health")
def health_check():
    from backend.storage.redis_client import redis
    total = redis.get("counter:total_analyses")
    return {
        "status": "ok",
        "service": "roast",
        "total_analyses": int(total) if total else 0,
    }


# ── Serve frontend static files ───────────────────────────────────────────────
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(str(_dist / "favicon.svg"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Don't intercept API or WebSocket routes
        if full_path.startswith("api/") or full_path.startswith("ws/") or full_path == "health":
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        return FileResponse(str(_dist / "index.html"))
