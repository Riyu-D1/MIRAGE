"""MIRAGE Backend API — FastAPI entrypoint, port 8000.

Run:  uvicorn app.main:app --port 8000   (from apps/backend/)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes import scans, sleeper, webhooks
from .schemas import HealthStatus

app = FastAPI(title="MIRAGE Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.artifacts_path.mkdir(parents=True, exist_ok=True)
app.mount(
    "/artifacts",
    StaticFiles(directory=str(settings.artifacts_path)),
    name="artifacts",
)


@app.get("/api/health", response_model=HealthStatus)
def health() -> HealthStatus:
    return HealthStatus(
        status="ok",
        service="mirage-backend",
        integrations={
            "supabase": settings.supabase_enabled,
            "grokbot": settings.grokbot_enabled,
            "tavily": settings.tavily_enabled,
            "companies_house": settings.companies_house_enabled,
        },
    )


app.include_router(scans.router, prefix="/api")
app.include_router(sleeper.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
