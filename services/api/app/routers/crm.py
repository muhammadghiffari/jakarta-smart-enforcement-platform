from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hmac
import hashlib
import os
from datetime import datetime, timezone
import uuid

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/v1/jaki", tags=["crm"])

# Mock Secret for demo - normally in env
JAKI_SECRET = b"demo-jaki-secret"

class JAKIReportIngest(BaseModel):
    jaki_report_id: str
    category: str
    lat: float
    lng: float
    photo_url: str
    description: str
    timestamp: str
    user_id_hashed: str

def verify_signature(request_body: bytes, signature: str):
    # In production, verify HMAC-SHA256
    # For demo we will accept it, but this is how you'd do it:
    # expected_signature = hmac.new(JAKI_SECRET, request_body, hashlib.sha256).hexdigest()
    # if not hmac.compare_digest(expected_signature, signature):
    #     raise HTTPException(status_code=401, detail="Invalid signature")
    pass

def map_category(raw_category: str) -> str:
    cat = raw_category.upper()
    if cat in ['PARKIR_LIAR', 'ILLEGAL_PARKING']: return 'ILLEGAL_PARKING'
    if cat in ['BUSWAY', 'BUSWAY_VIOLATION']: return 'BUSWAY_VIOLATION'
    if cat in ['SEPEDA', 'BICYCLE_LANE_VIOLATION']: return 'BICYCLE_LANE_VIOLATION'
    if cat in ['TURUN_NAIK_PENUMPANG', 'ILLEGAL_DROPOFF']: return 'ILLEGAL_DROPOFF'
    return 'OTHER'

@router.post("/ingest")
async def ingest_jaki_report(report: JAKIReportIngest, request: Request, x_jaki_signature: str = Header(None), db: Session = Depends(get_db)):
    """Ingest a public complaint from JAKI CRM Webhook."""
    body = await request.body()
    if x_jaki_signature:
        verify_signature(body, x_jaki_signature)

    norm_cat = map_category(report.category)

    # 1. Check if report already exists
    existing = db.query(models.CRMReport).filter(models.CRMReport.jaki_report_id == report.jaki_report_id).first()
    if existing:
        return {"status": "success", "message": "Report already exists", "id": existing.id}

    # 2. Corroborate with CCTV (Mock logic for demo)
    # Give a default citizen score of 0.8. Corroborate with CCTV -> 0.9.
    citizen_score = 0.8
    cctv_score = 0.9 # Mocking a positive CCTV corroboration
    alpha = 0.6
    combined = (alpha * citizen_score) + ((1 - alpha) * cctv_score)

    status = "VERIFIED" if combined >= 0.85 else "PENDING"

    crm_report = models.CRMReport(
        jaki_report_id=report.jaki_report_id,
        source="JAKI",
        category_raw=report.category,
        category_normalized=norm_cat,
        lat=report.lat,
        lng=report.lng,
        photo_url=report.photo_url,
        description=report.description,
        user_id_hashed=report.user_id_hashed,
        citizen_score=citizen_score,
        cctv_score=cctv_score,
        combined_confidence=combined,
        status=status
    )
    db.add(crm_report)

    # 3. Add Citizen Points (50 points per valid report)
    citizen = db.query(models.CitizenPoints).filter(models.CitizenPoints.user_id_hashed == report.user_id_hashed).first()
    if not citizen:
        citizen = models.CitizenPoints(
            user_id_hashed=report.user_id_hashed,
            points_total=50,
            reports_count=1,
            corroborated=1 if status == "VERIFIED" else 0
        )
        db.add(citizen)
    else:
        citizen.points_total += 50
        citizen.reports_count += 1
        if status == "VERIFIED":
            citizen.corroborated += 1

    # 4. If VERIFIED, dispatch to relevant unit
    if status == "VERIFIED" and norm_cat != "OTHER":
        legal_map = db.query(models.ViolationLegalMap).filter(models.ViolationLegalMap.violation_type == norm_cat).first()
        unit_code = legal_map.relevant_unit if legal_map else "general_operations"
        
        dispatch = models.UnitDispatch(
            crm_report_id=crm_report.id,
            unit_code=unit_code,
            status="DISPATCHED"
        )
        db.add(dispatch)

    db.commit()

    return {
        "status": "success",
        "message": "Report ingested and processed",
        "id": crm_report.id,
        "combined_confidence": combined,
        "assigned_unit": unit_code if status == "VERIFIED" and norm_cat != "OTHER" else None
    }


@router.get("/reports")
def list_crm_reports(limit: int = 50, skip: int = 0, db: Session = Depends(get_db)):
    """List all ingested citizen reports."""
    query = db.query(models.CRMReport)
    total = query.count()
    items = query.order_by(models.CRMReport.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": items, "total": total}


@router.get("/points")
def list_citizen_points(limit: int = 10, db: Session = Depends(get_db)):
    """Get the citizen leaderboard showing contribution points."""
    items = db.query(models.CitizenPoints).order_by(models.CitizenPoints.points_total.desc()).limit(limit).all()
    return {"items": items}


@router.get("/dispatches")
def list_dispatches(limit: int = 50, skip: int = 0, db: Session = Depends(get_db)):
    """List all operational unit dispatches with details resolved."""
    query = db.query(models.UnitDispatch)
    total = query.count()
    items = query.order_by(models.UnitDispatch.dispatched_at.desc()).offset(skip).limit(limit).all()
    
    dispatches_enriched = []
    for d in items:
        source_type = "SYSTEM (E-TLE)"
        details = ""
        violation_type = ""
        
        if d.violation_id:
            viol = db.query(models.Violation).filter(models.Violation.id == d.violation_id).first()
            if viol:
                violation_type = viol.violation_type
                details = f"Plate: {viol.track_id} | Cam: {viol.camera_id or 'Sudirman-01'}"
        elif d.crm_report_id:
            crm = db.query(models.CRMReport).filter(models.CRMReport.id == d.crm_report_id).first()
            if crm:
                source_type = "CITIZEN (JAKI)"
                violation_type = crm.category_normalized or crm.category or "OTHER"
                details = f"JAKI ID: {crm.jaki_report_id} | {crm.description[:40]}..."
                
        dispatches_enriched.append({
            "id": str(d.id),
            "violation_id": str(d.violation_id) if d.violation_id else None,
            "crm_report_id": str(d.crm_report_id) if d.crm_report_id else None,
            "unit_code": d.unit_code,
            "corridor": d.corridor or "Sudirman-Thamrin",
            "h3_cell": d.h3_cell or "8a2f15c2d1b7fff",
            "status": d.status,
            "dispatched_at": d.dispatched_at.isoformat() if d.dispatched_at else "",
            "acknowledged_at": d.acknowledged_at.isoformat() if d.acknowledged_at else None,
            "source_type": source_type,
            "violation_type": violation_type,
            "details": details
        })
        
    return {"items": dispatches_enriched, "total": total}
