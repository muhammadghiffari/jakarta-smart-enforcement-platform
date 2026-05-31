# services/api/app/schemas.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

class ViolationBase(BaseModel):
    id: UUID
    camera_id: Optional[str] = None
    track_id: str
    violation_type: str
    zone_id: Optional[UUID] = None
    vehicle_class: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str
    composite_confidence: Optional[float] = None
    legal_basis_code: Optional[str] = None
    sanction_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ViolationListResponse(BaseModel):
    items: List[ViolationBase]
    total: int

class DismissRequest(BaseModel):
    reason: str
    officer_id: str

class ConfirmRequest(BaseModel):
    officer_id: str
