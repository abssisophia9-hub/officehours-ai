"""
OfficeHours AI — Backend Entry Point

Run locally with:
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for the interactive API docs.
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database.migrate import ensure_schema
from app.database.session import Base, engine
from app.models import knowledge as _knowledge_model  # noqa: F401
from app.models import ta_roster as _ta_roster_model  # noqa: F401
from app.models import auth as _auth_model  # noqa: F401
from app.models import agent_metrics as _agent_metrics_model  # noqa: F401
from app.models import social as _social_model  # noqa: F401
from app.models import peer_notes as _peer_notes_model  # noqa: F401
from app.models import help_room as _help_room_model  # noqa: F401
from app.models import feedback as _feedback_model  # noqa: F401
from app.realtime.hub import set_main_loop
from app.routes.actions import router as actions_router
from app.routes.auth import courses_router, router as auth_router
from app.routes.canvas import router as canvas_router
from app.routes.lti import router as lti_router
from app.routes.feedback import router as feedback_router
from app.routes.knowledge import router as knowledge_router
from app.routes.office_hours import router as office_hours_router
from app.routes.peer_notes import router as peer_notes_router
from app.routes.help_room import router as help_room_router
from app.routes.realtime import router as realtime_router
from app.routes.requests import router as requests_router
from app.routes.ta import router as ta_router
from app.database.session import SessionLocal
from app.services.demo_accounts import ensure_demo_accounts
from app.services.demo_mode import demo_mode
from app.services.rate_limit import enforce_rate_limit

Base.metadata.create_all(bind=engine)
ensure_schema(engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    set_main_loop(asyncio.get_running_loop())
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="OfficeHours AI API",
    description="Backend API for the OfficeHours AI multi-role campus product.",
    version="0.2.0",
    lifespan=lifespan,
)

def _cors_origins() -> list[str]:
    front = (os.getenv("OFFICEHOURS_FRONTEND_URL") or "http://127.0.0.1:5180").rstrip("/")
    origins = {
        front,
        "http://127.0.0.1:5180",
        "http://localhost:5180",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    }
    extra = os.getenv("OFFICEHOURS_CORS_ORIGINS") or ""
    for part in extra.split(","):
        cleaned = part.strip().rstrip("/")
        if cleaned:
            origins.add(cleaned)
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_hot_paths(request: Request, call_next):
    try:
        enforce_rate_limit(request)
    except HTTPException as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)


@app.get("/")
def read_root():
    return {"status": "ok", "service": "OfficeHours AI API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "demo": demo_mode()}


app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(requests_router)
app.include_router(actions_router)
app.include_router(office_hours_router)
app.include_router(knowledge_router)
app.include_router(canvas_router)
app.include_router(lti_router)
app.include_router(ta_router)
app.include_router(peer_notes_router)
app.include_router(help_room_router)
app.include_router(feedback_router)
app.include_router(realtime_router)
