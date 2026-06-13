import os
import sys
from pathlib import Path

# Automatically add the repository root to Python's path so 'services.ai_pipeline' is found
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import violations, analytics, websocket, inference, legal, crm, reports, demo
from .database import engine
from . import models
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Ensure runs directory exists before mounting (uses absolute path so it works from any cwd)
RUNS_DIR = REPO_ROOT / "runs" / "pipeline"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="JSEP API", version="0.1.0")
scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup_create_tables():
    """Auto-create all tables on startup (idempotent). Skips gracefully if DB is offline."""
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as exc:
        import logging
        logging.getLogger("jsep.api").warning(
            "⚠️  Database not available (%s). "
            "API will start WITHOUT database features (violations queue, audit logs). "
            "Inference endpoints will still work.",
            exc,
        )
    
    # Start the hotspot computation background job
    scheduler.add_job(
        func=analytics.compute_hotspots_job,
        trigger=IntervalTrigger(minutes=15),
        id='compute_hotspots_job',
        name='Compute H3 KDE Hotspots every 15 minutes',
        replace_existing=True,
    )
    # Start scheduler
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()

# CORS — restrict to Vercel domain in production
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(violations.router)
app.include_router(analytics.router)
app.include_router(websocket.router)
app.include_router(inference.router)
app.include_router(legal.router)
app.include_router(crm.router)
app.include_router(reports.router)
app.include_router(demo.router)

app.mount("/runs", StaticFiles(directory=str(REPO_ROOT / "runs")), name="runs")

@app.get("/health")
def health():
    return {"status": "ok"}
