"""
OfficeHours AI — Backend Entry Point

Run locally with:
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for the interactive API docs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.session import Base, engine
from app.routes.actions import router as actions_router
from app.routes.office_hours import router as office_hours_router
from app.routes.requests import router as requests_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OfficeHours AI API",
    description="Backend API for the OfficeHours AI triage system.",
    version="0.1.0",
)

# Allow the frontend (kiosk + dashboard) to call this API during local dev.
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


app.include_router(requests_router)
app.include_router(actions_router)
app.include_router(office_hours_router)
