from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])

@router.get("/{violation_type}")
def get_legal_mapping(violation_type: str, db: Session = Depends(get_db)):
    """Fetch deterministic legal basis, sanction, and unit mapping for a violation type."""
    mapping = db.query(models.ViolationLegalMap).filter(models.ViolationLegalMap.violation_type == violation_type).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Legal mapping not found for this violation type")
        
    legal_ref = db.query(models.LegalReference).filter(models.LegalReference.code == mapping.legal_code).first()
    sanction_ref = db.query(models.SanctionReference).filter(models.SanctionReference.code == mapping.sanction_code).first()
    
    return {
        "violation_type": violation_type,
        "legal_basis": {
            "code": legal_ref.code if legal_ref else None,
            "title": legal_ref.title if legal_ref else None,
            "citation_text": legal_ref.citation_text if legal_ref else None
        },
        "sanction": {
            "code": sanction_ref.code if sanction_ref else None,
            "title": sanction_ref.title if sanction_ref else None,
            "fine_min_idr": sanction_ref.fine_min_idr if sanction_ref else None,
            "fine_max_idr": sanction_ref.fine_max_idr if sanction_ref else None,
            "action_type": sanction_ref.action_type if sanction_ref else None
        },
        "relevant_unit": mapping.relevant_unit,
        "evidence_required": mapping.evidence_required,
        "static_report_fragment": mapping.static_report_fragment
    }

@router.get("")
def list_legal_mappings(db: Session = Depends(get_db)):
    """List all legal mappings and details."""
    mappings = db.query(models.ViolationLegalMap).all()
    results = []
    for mapping in mappings:
        legal_ref = db.query(models.LegalReference).filter(models.LegalReference.code == mapping.legal_code).first()
        sanction_ref = db.query(models.SanctionReference).filter(models.SanctionReference.code == mapping.sanction_code).first()
        results.append({
            "violation_type": mapping.violation_type,
            "legal_basis": {
                "code": legal_ref.code if legal_ref else None,
                "title": legal_ref.title if legal_ref else None,
                "citation_text": legal_ref.citation_text if legal_ref else None
            },
            "sanction": {
                "code": sanction_ref.code if sanction_ref else None,
                "title": sanction_ref.title if sanction_ref else None,
                "fine_min_idr": sanction_ref.fine_min_idr if sanction_ref else None,
                "fine_max_idr": sanction_ref.fine_max_idr if sanction_ref else None,
                "action_type": sanction_ref.action_type if sanction_ref else None
            },
            "relevant_unit": mapping.relevant_unit,
            "evidence_required": mapping.evidence_required
        })
    return {"items": results}
