# services/api/app/routers/analytics.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import json
import h3
import numpy as np
from scipy.stats import gaussian_kde
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, value, GLPK
from pathlib import Path
import os

from ..database import get_db, SessionLocal
from .. import models

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def compute_hotspots_job():
    """
    Background job to compute hotspots from recent violations.
    Runs every 15 minutes.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24) # Look at last 24 hours for KDE

        # 1. Fetch violations with coordinates (join with Camera)
        violations = db.query(models.Violation, models.Camera).join(
            models.Camera, models.Violation.camera_id == models.Camera.id
        ).filter(models.Violation.start_time >= since).all()

        if not violations:
            return # No data to compute

        # Step 1: Map violations to H3 cells (Resolution 10 and 9)
        # We'll compute for Resolution 10 to store in DB
        cell_events = {}
        for viol, cam in violations:
            if cam.location_lat is None or cam.location_lng is None:
                continue
            
            # Use h3 v4 API
            cell = h3.latlng_to_cell(cam.location_lat, cam.location_lng, 10)
            if cell not in cell_events:
                cell_events[cell] = []
            cell_events[cell].append(viol)

        if not cell_events:
            return

        # Step 2: Temporal decay
        for cell, events in cell_events.items():
            for e in events:
                age_hours = (now - e.start_time).total_seconds() / 3600.0
                e._weight = np.exp(-0.1 * age_hours)

        # Step 3: KDE on H3 cell centroids
        coords = np.array([h3.cell_to_latlng(c) for c in cell_events.keys()])
        weights = np.array([sum(e._weight for e in evs) for evs in cell_events.values()])
        
        # Add a tiny bit of noise if all points are identical to avoid singular matrix in KDE
        if len(coords) > 1 and np.all(coords == coords[0]):
            coords = coords + np.random.normal(0, 1e-5, coords.shape)
            
        if len(coords) > 1:
            try:
                kde = gaussian_kde(coords.T, weights=weights, bw_method='scott')
                kde_density = kde(coords.T)
                max_density = kde_density.max() if kde_density.max() > 0 else 1.0
            except np.linalg.LinAlgError:
                kde_density = weights
                max_density = weights.max() if weights.max() > 0 else 1.0
        else:
            kde_density = [1.0]
            max_density = 1.0

        # Step 4: Composite risk score
        severity_weights = {'CRITICAL': 1.5, 'HIGH': 1.0, 'MEDIUM': 0.6}
        # In DB we don't store severity directly, we map by violation_type for demo
        type_severity = {
            'BUSWAY_VIOLATION': 1.5,
            'ILLEGAL_PARKING': 1.0,
            'BICYCLE_LANE_VIOLATION': 1.0,
            'ILLEGAL_DROPOFF': 0.6
        }

        bucket_time = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)

        for i, cell in enumerate(cell_events.keys()):
            recency = np.mean([e._weight for e in cell_events[cell]])
            severity = np.mean([type_severity.get(e.violation_type, 1.0) for e in cell_events[cell]])
            
            risk = (
                0.5 * (kde_density[i] / max_density) +
                0.3 * recency +
                0.2 * min(severity / 1.5, 1.0)
            )
            count = len(cell_events[cell])
            
            # Upsert into H3Hotspot
            existing = db.query(models.H3Hotspot).filter(
                models.H3Hotspot.h3_index == cell,
                models.H3Hotspot.resolution == 10,
                models.H3Hotspot.bucket == bucket_time
            ).first()
            
            if existing:
                existing.risk_score = float(risk)
                existing.count = count
            else:
                new_hotspot = models.H3Hotspot(
                    h3_index=cell,
                    resolution=10,
                    bucket=bucket_time,
                    risk_score=float(risk),
                    count=count,
                    corridor="Generated"
                )
                db.add(new_hotspot)
        
        db.commit()

    except Exception as e:
        print(f"Error computing hotspots: {e}")
        db.rollback()
    finally:
        db.close()


@router.get("/hotspots")
def get_hotspots(resolution: int = 10, hours: int = 1, db: Session = Depends(get_db)):
    """
    Returns aggregated H3 hotspots over the last N hours.
    Used by the dashboard MapLibre heatmap.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Aggregate risk_score and count per h3_index within the time window
    results = db.query(
        models.H3Hotspot.h3_index,
        func.sum(models.H3Hotspot.count).label("total_count"),
        func.avg(models.H3Hotspot.risk_score).label("avg_risk")
    ).filter(
        models.H3Hotspot.resolution == resolution,
        models.H3Hotspot.bucket >= since
    ).group_by(models.H3Hotspot.h3_index).all()

    hotspots = {}
    for r in results:
        hotspots[r.h3_index] = float(r.avg_risk)

    return {"hotspots": hotspots}


@router.get("/optimizer")
def run_mclp_optimizer(n_officers: int = 5, db: Session = Depends(get_db)):
    """
    Runs the Maximal Covering Location Problem (MCLP) to suggest
    officer deployment locations based on recent hotspots.
    """
    # 1. Gather demand from H3Hotspot (Resolution 10)
    recent_hotspots = db.query(
        models.H3Hotspot.h3_index,
        func.avg(models.H3Hotspot.risk_score).label("avg_risk")
    ).filter(
        models.H3Hotspot.bucket >= datetime.now(timezone.utc) - timedelta(hours=2)
    ).group_by(models.H3Hotspot.h3_index).all()

    if not recent_hotspots:
        return {"recommended_deployments": [], "message": "No recent hotspot data available."}

    demand_cells = {h.h3_index: float(h.avg_risk) for h in recent_hotspots}

    # 2. Load candidate positions from designated_stops.geojson
    repo_root = Path(__file__).resolve().parents[4]
    stops_file = repo_root / "fixtures" / "designated_stops.geojson"
    
    candidate_positions = []
    candidates_data = {}
    
    if stops_file.exists():
        with open(stops_file, "r") as f:
            data = json.load(f)
            for feature in data.get("features", []):
                coords = feature.get("geometry", {}).get("coordinates")
                props = feature.get("properties", {})
                if coords and len(coords) == 2:
                    lng, lat = coords
                    # Get H3 cell for candidate
                    cell = h3.latlng_to_cell(lat, lng, 10)
                    if cell not in candidates_data:
                        candidates_data[cell] = {
                            "lat": lat, "lng": lng,
                            "name": props.get("lokasi_alamat", "Designated Stop")
                        }
                        candidate_positions.append(cell)
    
    # Fallback to demand cells if no candidates
    if not candidate_positions:
        candidate_positions = list(demand_cells.keys())

    # 3. Formulate MCLP Problem using PuLP
    prob = LpProblem("MCLP_Officer_Placement", LpMaximize)
    x = {pos: LpVariable(f"x_{pos}", cat='Binary') for pos in candidate_positions}
    y = {cell: LpVariable(f"y_{cell}", cat='Binary') for cell in demand_cells}

    # Objective: maximize covered demand
    prob += lpSum(demand_cells[c] * y[c] for c in demand_cells)

    # Coverage constraint: 500m radius
    # In H3 Res 10, edge length is ~66m. A 500m radius is roughly k=7 rings.
    # We will use h3.grid_disk to find covering cells.
    for cell in demand_cells:
        covering_cells = h3.grid_disk(cell, 7)
        covering_officers = [pos for pos in candidate_positions if pos in covering_cells]
        if covering_officers:
            prob += y[cell] <= lpSum(x[pos] for pos in covering_officers)
        else:
            prob += y[cell] == 0

    # Officer count constraint
    prob += lpSum(x.values()) <= n_officers

    # 4. Solve Problem
    # Use GLPK if installed, else fallback to default CBC
    prob.solve()

    # 5. Extract Results
    suggestions = []
    for pos, var in x.items():
        if value(var) == 1.0:
            cdata = candidates_data.get(pos, {"name": "Hotspot Area"})
            suggestions.append({
                "h3_index": pos,
                "corridor": cdata["name"][:50], # Truncate for display
                "priority": "HIGH",
                "reasoning": f"Optimized coverage for high-demand zones."
            })

    # Sort suggestions by demand covered (approximation)
    suggestions.sort(key=lambda s: demand_cells.get(s["h3_index"], 0), reverse=True)

    return {"recommended_deployments": suggestions}
