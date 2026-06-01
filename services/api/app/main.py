from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import violations, analytics, websocket, inference

app = FastAPI(title="JSEP API", version="0.1.0")

# Allow CORS for dashboard (frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(violations.router)
app.include_router(analytics.router)
app.include_router(websocket.router)
app.include_router(inference.router)
@app.get("/health")
def health():
    return {"status": "ok"}
