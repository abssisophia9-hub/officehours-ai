"""
OfficeHours AI — Backend Entry Point

Run locally with:
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for the interactive API docs.
"""

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
from app.models import notification as _notification_model  # noqa: F401
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
from app.routes.notifications import router as notifications_router
from app.database.session import SessionLocal
from app.services.demo_accounts import ensure_demo_accounts
from app.services.demo_mode import demo_mode
from app.services.rate_limit import enforce_rate_limit
from app.services.security_log import audit

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
    # Never expose OpenAPI exception internals; keep docs available for operators.
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


def _public_error(detail: str, status_code: int) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    if exc.status_code >= 500:
        audit(
            "http.error",
            level="error",
            path=str(request.url.path),
            status=exc.status_code,
            request_id=getattr(request.state, "request_id", None),
        )
        detail = "Internal server error."
    return _public_error(detail, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Keep field errors for API clients; never include body secrets.
    return JSONResponse(
        {"detail": exc.errors()},
        status_code=422,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    audit(
        "http.unhandled",
        level="error",
        path=str(request.url.path),
        error_type=type(exc).__name__,
        request_id=getattr(request.state, "request_id", None),
    )
    return _public_error("Internal server error.", 500)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        enforce_rate_limit(request)
    except HTTPException as exc:
        response = _public_error(
            exc.detail if isinstance(exc.detail, str) else "Too many requests.",
            exc.status_code,
        )
        response.headers["X-Request-Id"] = request_id
        return response

    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    if response.status_code >= 500:
        audit(
            "http.response",
            level="error",
            path=request.url.path,
            method=request.method,
            status=response.status_code,
            ms=elapsed_ms,
            request_id=request_id,
        )
    elif response.status_code in {401, 403}:
        audit(
            "http.denied",
            level="warning",
            path=request.url.path,
            method=request.method,
            status=response.status_code,
            ms=elapsed_ms,
            request_id=request_id,
        )
    return response


@app.get("/")
def read_root():
    return {"status": "ok", "service": "OfficeHours AI API"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "demo": demo_mode(),
        "database": engine.dialect.name,
        "rate_limit": os.getenv("OFFICEHOURS_RATE_LIMIT", "true").strip().lower()
        not in {"0", "false", "no", "off"},
    }


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
app.include_router(notifications_router)
app.include_router(realtime_router)
