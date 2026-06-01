from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid
import time
import httpx

from ..database import get_db
from .. import models, schemas
from .websocket import manager

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

# Internal base URL for triggering endpoints
API_BASE_URL = "http://localhost:8000"

async def run_scenario_a():
    # Scenario A: Illegal Parking (30s)
    # Simulate an internal event sent from the AI pipeline
    payload = {
        "id": str(uuid.uuid4()),
        "camera_id": "CAM-JKT-SUDIRMAN-01",
        "track_id": "B 1234 XYZ",
        "violation_type": "ILLEGAL_PARKING",
        "zone_id": str(uuid.uuid4()), # Mock zone
        "vehicle_class": "car",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 35,
        "status": "DETECTED",
        "composite_confidence": 0.92
    }
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_BASE_URL}/api/v1/violations/internal/event", json=payload)

async def run_scenario_b():
    # Scenario B: Busway Lane Violation
    payload = {
        "id": str(uuid.uuid4()),
        "camera_id": "CAM-JKT-THAMRIN-02",
        "track_id": "B 9999 ABC",
        "violation_type": "BUSWAY_VIOLATION",
        "zone_id": str(uuid.uuid4()),
        "vehicle_class": "motorcycle",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 5,
        "status": "DETECTED",
        "composite_confidence": 0.88
    }
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_BASE_URL}/api/v1/violations/internal/event", json=payload)

async def run_scenario_c():
    # Scenario C: Illegal Pick-up/Drop-off
    payload = {
        "id": str(uuid.uuid4()),
        "camera_id": "CAM-JKT-GATOT-03",
        "track_id": "B 7777 DEF",
        "violation_type": "ILLEGAL_DROPOFF",
        "zone_id": str(uuid.uuid4()),
        "vehicle_class": "angkot",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 25,
        "status": "DETECTED",
        "composite_confidence": 0.85
    }
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_BASE_URL}/api/v1/violations/internal/event", json=payload)

async def run_scenario_e():
    # Scenario E: JAKI CRM Webhook
    payload = {
        "jaki_report_id": f"JAKI-{uuid.uuid4().hex[:8]}",
        "category": "PARKIR_LIAR",
        "lat": -6.2088,
        "lng": 106.8456,
        "photo_url": "https://jsep.dishub.go.id/mock_photo.jpg",
        "description": "Mobil parkir sembarangan di trotoar",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id_hashed": "hash12345"
    }
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_BASE_URL}/api/v1/jaki/ingest", json=payload)

async def execute_demo_sequence(scenario: str):
    if scenario == "A":
        await run_scenario_a()
    elif scenario == "B":
        await run_scenario_b()
    elif scenario == "C":
        await run_scenario_c()
    elif scenario == "E":
        await run_scenario_e()

@router.post("/trigger/{scenario}")
async def trigger_scenario(scenario: str, background_tasks: BackgroundTasks):
    """Safely trigger a demo scenario by injecting mock data. Does not interfere with real pipeline."""
    scenario = scenario.upper()
    if scenario not in ["A", "B", "C", "D", "E"]:
        raise HTTPException(status_code=400, detail="Invalid scenario. Must be A, B, C, D, or E.")
    
    # Run in background to immediately return success to UI
    background_tasks.add_task(execute_demo_sequence, scenario)
    return {"status": "success", "message": f"Scenario {scenario} triggered"}
