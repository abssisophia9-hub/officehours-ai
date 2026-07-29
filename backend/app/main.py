"""
OfficeHours AI — Backend Entry Point

Run locally with:
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for the interactive API docs.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.migrate import ensure_schema
from app.database.session import Base, engine
from app.models import knowledge as _knowledge_model  # noqa: F401
from app.models import ta_roster as _ta_roster_model  # noqa: F401
from app.models import auth as _auth_model  # noqa: F401
from app.models import agent_metrics as _agent_metrics_model  # noqa: F401
from app.realtime.hub import set_main_loop
from app.routes.actions import router as actions_router
from app.routes.auth import courses_router, router as auth_router
from app.routes.canvas import router as canvas_router
from app.routes.knowledge import router as knowledge_router
from app.routes.office_hours import router as office_hours_router
from app.routes.realtime import router as realtime_router
from app.routes.requests import router as requests_router
from app.routes.ta import router as ta_router
from app.database.session import SessionLocal
from app.services.demo_accounts import ensure_demo_accounts

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

# Allow the frontend (kiosk + dashboards) to call this API during local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "ok", "service": "OfficeHours AI API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(requests_router)
app.include_router(actions_router)
app.include_router(office_hours_router)
app.include_router(knowledge_router)
app.include_router(canvas_router)
app.include_router(ta_router)
app.include_router(realtime_router)
