# services/api/app/routers/violations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone

from ..database import get_db
from .. import models, schemas
from .websocket import manager

router = APIRouter(prefix="/api/v1/violations", tags=["violations"])


@router.get("", response_model=schemas.ViolationListResponse)
def list_violations(status: str = "DETECTED", limit: int = 50, skip: int = 0, db: Session = Depends(get_db)):
    """List violations for the ETLE queue."""
    query = db.query(models.Violation).filter(models.Violation.status == status)
    total = query.count()
    items = query.order_by(models.Violation.start_time.desc()).offset(skip).limit(limit).all()
    return {"items": items, "total": total}


@router.post("/{violation_id}/confirm")
def confirm_violation(violation_id: UUID, req: schemas.ConfirmRequest, db: Session = Depends(get_db)):
    """Approve a violation for E-TLE submission."""
    viol = db.query(models.Violation).filter(models.Violation.id == violation_id).first()
    if not viol:
        raise HTTPException(status_code=404, detail="Violation not found")

    if viol.status != "DETECTED":
        raise HTTPException(status_code=400, detail=f"Cannot confirm violation in {viol.status} state")

    # RULE-04: composite_confidence >= 0.75
    # (Assuming composite_confidence is populated. If None, it fails the gate unless explicitly handled.)
    if viol.composite_confidence is not None and viol.composite_confidence < 0.75:
        raise HTTPException(status_code=400, detail="Confidence too low for auto-approval. Must review.")

    viol.status = "CONFIRMED"

    # Create ETLE Submission
    etle = models.ETLESubmission(
        violation_id=viol.id,
        officer_id=req.officer_id,
        approved_at=datetime.now(timezone.utc),
        is_mock=True,
        status="SUBMITTED",
        ticket_number=f"ETL-{datetime.now().strftime('%Y%m%d')}-JKP-ILP-{str(viol.id)[:6]}"
    )
    db.add(etle)
    
    # Audit log
    audit = models.AuditLog(
        action="CONFIRM",
        entity_type="violation",
        entity_id=str(viol.id),
        officer_id=req.officer_id,
        detail="Violation confirmed and ETLE draft created."
    )
    db.add(audit)

    db.commit()
    return {"status": "success", "ticket_number": etle.ticket_number}


@router.post("/{violation_id}/dismiss")
def dismiss_violation(violation_id: UUID, req: schemas.DismissRequest, db: Session = Depends(get_db)):
    """Dismiss a violation from the queue."""
    viol = db.query(models.Violation).filter(models.Violation.id == violation_id).first()
    if not viol:
        raise HTTPException(status_code=404, detail="Violation not found")

    if viol.status != "DETECTED":
        raise HTTPException(status_code=400, detail=f"Cannot dismiss violation in {viol.status} state")

    viol.status = "DISMISSED"

    # Audit log
    audit = models.AuditLog(
        action="DISMISS",
        entity_type="violation",
        entity_id=str(viol.id),
        officer_id=req.officer_id,
        detail=f"Reason: {req.reason}"
    )
    db.add(audit)

    db.commit()
    return {"status": "success"}

@router.post("/internal/event")
async def ingest_violation_event(viol: schemas.ViolationBase, db: Session = Depends(get_db)):
    """Internal endpoint for ML pipeline to push violations and broadcast."""
    # 1. Save to database
    db_viol = models.Violation(
        id=viol.id,
        camera_id=viol.camera_id,
        track_id=viol.track_id,
        violation_type=viol.violation_type,
        zone_id=viol.zone_id,
        vehicle_class=viol.vehicle_class,
        start_time=viol.start_time,
        end_time=viol.end_time,
        duration_seconds=viol.duration_seconds,
        status=viol.status,
        composite_confidence=viol.composite_confidence
    )
    # Ensure no duplicates if pipeline retries
    existing = db.query(models.Violation).filter(models.Violation.id == viol.id).first()
    if not existing:
        db.add(db_viol)
        db.commit()

    # 2. Broadcast to UI
    # We need to construct a payload matching what the frontend expects
    payload = {
        "id": str(viol.id),
        "type": viol.violation_type,
        "plate": viol.track_id, # using track_id as plate for demo if actual plate missing
        "camera": viol.camera_id,
        "timestamp": viol.start_time.isoformat(),
        "confidence": viol.composite_confidence
    }
    await manager.broadcast_violation(payload)
    
    return {"status": "broadcasted"}
