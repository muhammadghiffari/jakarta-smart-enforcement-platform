# services/api/app/routers/analytics.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


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
    # Simple placeholder algorithm for demo
    # Real MCLP would use PuLP or similar to maximize coverage
    recent_hotspots = db.query(
        models.H3Hotspot.h3_index,
        models.H3Hotspot.corridor,
        func.avg(models.H3Hotspot.risk_score).label("avg_risk")
    ).filter(
        models.H3Hotspot.bucket >= datetime.now(timezone.utc) - timedelta(hours=2)
    ).group_by(models.H3Hotspot.h3_index, models.H3Hotspot.corridor)\
     .order_by(func.avg(models.H3Hotspot.risk_score).desc())\
     .limit(n_officers).all()

    suggestions = []
    for h in recent_hotspots:
        suggestions.append({
            "h3_index": h.h3_index,
            "corridor": h.corridor,
            "priority": "HIGH",
            "reasoning": "High concentration of active violations."
        })

    return {"recommended_deployments": suggestions}
