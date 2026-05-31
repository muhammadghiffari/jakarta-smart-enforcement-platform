# services/api/app/models.py
# SQLAlchemy ORM models — mirrors PRD Section 12.1 DDL
# TimescaleDB hypertables (violations, h3_hotspots) created via Alembic migration.

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float,
    ForeignKey, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _now():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# cameras
# --------------------------------------------------------------------------- #
class Camera(Base):
    __tablename__ = "cameras"

    id             = Column(String(64),  primary_key=True)
    name           = Column(String(128), nullable=False)
    location_lat   = Column(Float)
    location_lng   = Column(Float)
    corridor       = Column(String(64))
    rtsp_url       = Column(Text)
    hls_url        = Column(Text)
    # A=excellent B=good C=degraded D=offline — PRD Section 7.2
    readiness_grade= Column(String(1), default="B")
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), default=_now)

    violations = relationship("Violation", back_populates="camera", lazy="dynamic")


# --------------------------------------------------------------------------- #
# zones
# --------------------------------------------------------------------------- #
class Zone(Base):
    __tablename__ = "zones"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(128))
    zone_type   = Column(String(32), nullable=False)   # NO_PARKING | BUSWAY_LANE | …
    threshold_s = Column(Integer, default=30)
    corridor    = Column(String(64))
    # geometry stored as GeoJSON text for portability (PostGIS geom in migration)
    geojson     = Column(Text)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), default=_now)


# --------------------------------------------------------------------------- #
# violations  (TimescaleDB hypertable on start_time)
# --------------------------------------------------------------------------- #
class Violation(Base):
    __tablename__ = "violations"
    __table_args__ = (
        CheckConstraint(
            "violation_type IN ('ILLEGAL_PARKING','BUSWAY_VIOLATION',"
            "'BICYCLE_LANE_VIOLATION','ILLEGAL_DROPOFF','GANJIL_GENAP')",
            name="ck_violation_type",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id            = Column(String(64), ForeignKey("cameras.id"), nullable=True)
    track_id             = Column(String(64), nullable=False)
    violation_type       = Column(String(32), nullable=False)
    zone_id              = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    vehicle_class        = Column(String(32))
    start_time           = Column(DateTime(timezone=True), nullable=False, default=_now)
    end_time             = Column(DateTime(timezone=True), nullable=True)
    duration_seconds     = Column(Integer)
    status               = Column(String(32), default="DETECTED")   # DETECTED|CONFIRMED|DISMISSED|ETLE_SUBMITTED
    composite_confidence = Column(Numeric(4, 3))
    legal_basis_code     = Column(String(64))
    sanction_code        = Column(String(64))
    created_at           = Column(DateTime(timezone=True), default=_now)

    camera      = relationship("Camera", back_populates="violations")
    anpr_result = relationship("ANPRResult", back_populates="violation", uselist=False)
    evidence    = relationship("EvidencePackage", back_populates="violation", uselist=False)
    etle        = relationship("ETLESubmission", back_populates="violation", uselist=False)


# --------------------------------------------------------------------------- #
# anpr_results
# --------------------------------------------------------------------------- #
class ANPRResult(Base):
    __tablename__ = "anpr_results"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    violation_id         = Column(UUID(as_uuid=True), ForeignKey("violations.id"), nullable=False)
    plate_raw            = Column(String(32))
    plate_cleaned        = Column(String(32))
    is_valid_format      = Column(Boolean, default=False)
    ocr_confidence       = Column(Numeric(4, 3))
    quality_score        = Column(Numeric(4, 3))
    composite_confidence = Column(Numeric(4, 3))
    needs_human_review   = Column(Boolean, default=True)
    rejection_reason     = Column(String(64))
    created_at           = Column(DateTime(timezone=True), default=_now)

    violation = relationship("Violation", back_populates="anpr_result")


# --------------------------------------------------------------------------- #
# evidence_packages
# --------------------------------------------------------------------------- #
class EvidencePackage(Base):
    __tablename__ = "evidence_packages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    violation_id    = Column(UUID(as_uuid=True), ForeignKey("violations.id"), nullable=False)
    best_frame_url  = Column(Text)
    video_clip_url  = Column(Text)
    # SHA-256 hash of the video file — PRD RULE-08
    video_hash_sha256 = Column(String(64))
    plate_crop_url  = Column(Text)
    created_at      = Column(DateTime(timezone=True), default=_now)

    violation = relationship("Violation", back_populates="evidence")


# --------------------------------------------------------------------------- #
# etle_submissions
# --------------------------------------------------------------------------- #
class ETLESubmission(Base):
    __tablename__ = "etle_submissions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    violation_id    = Column(UUID(as_uuid=True), ForeignKey("violations.id"), nullable=False)
    ticket_number   = Column(String(64), unique=True)
    officer_id      = Column(String(64))
    approved_at     = Column(DateTime(timezone=True))
    # Always True in demo — PRD Section 12.1, RULE-02
    is_mock         = Column(Boolean, default=True)
    status          = Column(String(32), default="DRAFT")   # DRAFT|SUBMITTED|REJECTED
    created_at      = Column(DateTime(timezone=True), default=_now)

    violation = relationship("Violation", back_populates="etle")


# --------------------------------------------------------------------------- #
# h3_hotspots  (TimescaleDB hypertable on bucket)
# --------------------------------------------------------------------------- #
class H3Hotspot(Base):
    __tablename__ = "h3_hotspots"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    h3_index    = Column(String(16), nullable=False)
    resolution  = Column(Integer, nullable=False)   # 9 or 10
    bucket      = Column(DateTime(timezone=True), nullable=False)   # 15-min bucket
    risk_score  = Column(Float, default=0.0)
    count       = Column(Integer, default=0)
    corridor    = Column(String(64))

    __table_args__ = (
        UniqueConstraint("h3_index", "resolution", "bucket", name="uq_h3_bucket"),
    )


# --------------------------------------------------------------------------- #
# crm_reports
# --------------------------------------------------------------------------- #
class CRMReport(Base):
    __tablename__ = "crm_reports"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jaki_report_id  = Column(String(64), unique=True)
    category        = Column(String(64))
    lat             = Column(Float)
    lng             = Column(Float)
    photo_url       = Column(Text)
    description     = Column(Text)
    # SHA-256 of user_id — no real PII stored — PRD FR-VIO-08
    user_id_hashed  = Column(String(64))
    status          = Column(String(32), default="RECEIVED")
    corroborated_violation_id = Column(UUID(as_uuid=True), ForeignKey("violations.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), default=_now)


# --------------------------------------------------------------------------- #
# unit_dispatches
# --------------------------------------------------------------------------- #
class UnitDispatch(Base):
    __tablename__ = "unit_dispatches"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    violation_id    = Column(UUID(as_uuid=True), ForeignKey("violations.id"), nullable=True)
    unit_code       = Column(String(64))
    corridor        = Column(String(64))
    h3_cell         = Column(String(16))
    status          = Column(String(32), default="DISPATCHED")
    dispatched_at   = Column(DateTime(timezone=True), default=_now)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)


# --------------------------------------------------------------------------- #
# citizen_points  (replaces blockchain/SBT — PRD RULE-10)
# --------------------------------------------------------------------------- #
class CitizenPoints(Base):
    __tablename__ = "citizen_points"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id_hashed = Column(String(64), nullable=False, unique=True)
    points_total   = Column(Integer, default=0)
    reports_count  = Column(Integer, default=0)
    corroborated   = Column(Integer, default=0)
    updated_at     = Column(DateTime(timezone=True), default=_now, onupdate=_now)


# --------------------------------------------------------------------------- #
# audit_log  (append-only — PRD RULE-09; PostgreSQL RULES enforced in migration)
# --------------------------------------------------------------------------- #
class AuditLog(Base):
    __tablename__ = "audit_log"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action      = Column(String(64), nullable=False)
    entity_type = Column(String(64))
    entity_id   = Column(String(64))
    officer_id  = Column(String(64))
    detail      = Column(Text)
    created_at  = Column(DateTime(timezone=True), default=_now)
