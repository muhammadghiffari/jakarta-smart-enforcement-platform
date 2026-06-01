import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import violations, analytics, websocket, inference, legal, crm, reports, demo
from .database import engine
from . import models

app = FastAPI(title="JSEP API", version="0.1.0")

@app.on_event("startup")
def startup_create_tables():
    """Auto-create all tables on startup (idempotent)."""
    models.Base.metadata.create_all(bind=engine)

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

@app.get("/health")
def health():
    return {"status": "ok"}
