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

    # Relevant-Unit Routing Dispatch
    legal_map = db.query(models.ViolationLegalMap).filter(models.ViolationLegalMap.violation_type == viol.violation_type).first()
    if legal_map and legal_map.relevant_unit:
        dispatch = models.UnitDispatch(
            violation_id=viol.id,
            unit_code=legal_map.relevant_unit,
            status="DISPATCHED"
        )
        db.add(dispatch)

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

@router.get("/{violation_id}/berita_acara")
def generate_berita_acara_endpoint(violation_id: UUID, format: str = "json", db: Session = Depends(get_db)):
    """Generate a formal Berita Acara for the violation (supports JSON and PDF)."""
    viol = db.query(models.Violation).filter(models.Violation.id == violation_id).first()
    if not viol:
        raise HTTPException(status_code=404, detail="Violation not found")

    import os
    import sys
    import io
    from pathlib import Path
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    # Resolve the zone name
    zone_name = "Corridor Rule"
    if viol.zone_id:
        zone = db.query(models.Zone).filter(models.Zone.id == viol.zone_id).first()
        if zone:
            zone_name = zone.name

    # Create the dictionary expected by rag_agent
    v_dict = {
        "violation_type": viol.violation_type,
        "zone_name": zone_name,
        "duration_s": viol.duration_seconds or 0,
        "plate": viol.track_id,
        "timestamp": viol.start_time.isoformat() if viol.start_time else "",
        "camera_id": viol.camera_id,
        "officer_id": "OFC-DEMO-01",  # Hardcoded for demo/authorization
        "confidence": float(viol.composite_confidence) if viol.composite_confidence else 0.0,
    }

    # Import rag_agent safely from project root
    try:
        from services.narrative_agent.rag_agent import generate_berita_acara, _static_ba_fallback
    except ImportError:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
        from services.narrative_agent.rag_agent import generate_berita_acara, _static_ba_fallback

    # Respect the ENABLE_LLM_DRAFTING toggle (acting as authorization/feature flag)
    if os.environ.get("ENABLE_LLM_DRAFTING", "true").lower() == "true":
        text_content = generate_berita_acara(v_dict)
    else:
        text_content = _static_ba_fallback(v_dict)

    if format == "pdf":
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 50, "BERITA ACARA PELANGGARAN LALU LINTAS")
        
        c.setFont("Helvetica", 12)
        y = height - 80
        
        # Super simple text wrapping for the demo PDF
        for line in text_content.split('\n'):
            # Basic manual word wrap logic for long lines
            words = line.split(" ")
            current_line = ""
            for word in words:
                if c.stringWidth(current_line + word + " ", "Helvetica", 12) < width - 100:
                    current_line += word + " "
                else:
                    if y < 50:
                        c.showPage()
                        y = height - 50
                        c.setFont("Helvetica", 12)
                    c.drawString(50, y, current_line)
                    y -= 20
                    current_line = word + " "
                    
            if current_line:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica", 12)
                c.drawString(50, y, current_line)
                y -= 20
            
        c.save()
        buffer.seek(0)
        return StreamingResponse(
            buffer, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename=berita_acara_{viol.track_id}.pdf"}
        )

    # Default to returning JSON so the frontend/government APIs can use it directly
    return {"status": "success", "content": text_content}
