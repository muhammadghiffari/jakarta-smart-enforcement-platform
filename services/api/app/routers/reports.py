import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

@router.get("/executive")
def generate_executive_report(db: Session = Depends(get_db)):
    """Generate daily executive summary PDF report."""
    
    # 1. Fetch data for report
    total_violations = db.query(models.Violation).count()
    verified_violations = db.query(models.Violation).filter(models.Violation.status == 'CONFIRMED').count()
    citizen_reports = db.query(models.CRMReport).count()
    
    # 2. Generate PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "JSEP Executive Summary Report")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    c.drawString(50, height - 120, "1. Trial Monitoring Results")
    c.drawString(70, height - 140, f"- Total Detected Violations: {total_violations}")
    c.drawString(70, height - 160, f"- Confirmed / E-TLE Ready: {verified_violations}")
    
    c.drawString(50, height - 200, "2. Public Reporting Participation")
    c.drawString(70, height - 220, f"- Total Citizen Reports (JAKI/CRM): {citizen_reports}")
    
    c.drawString(50, height - 260, "3. Hotspots & Behaviour Statistics")
    c.drawString(70, height - 280, "- (See Dashboard for full H3 mapping resolution 9 and 10)")
    
    # Optional Narrative (deterministic or LLM) can go here
    
    c.save()
    
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=jsep_executive_summary.pdf"})
