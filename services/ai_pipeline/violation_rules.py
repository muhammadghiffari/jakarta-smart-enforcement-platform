# services/ai_pipeline/violation_rules.py
# JSEP deterministic violation rule engine — PRD Section 6.3
#
# NOT a neural classifier. Every decision is rule-based and auditable.
# The engine checks track state against zone type and threshold.
# Legal lookups come from legal_reference/violation_legal_map.yaml (FR-LEGAL-01).

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("jsep.rules")


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class ViolationType(str, Enum):
    ILLEGAL_PARKING        = "ILLEGAL_PARKING"
    BUSWAY_VIOLATION       = "BUSWAY_VIOLATION"
    BICYCLE_LANE_VIOLATION = "BICYCLE_LANE_VIOLATION"
    ILLEGAL_DROPOFF        = "ILLEGAL_DROPOFF"
    GANJIL_GENAP           = "GANJIL_GENAP"   # future-only — not wired in v1


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #
@dataclass
class VehicleTrack:
    """
    Represents the current state of a tracked vehicle.
    Updated by the pipeline on each frame tick.
    """
    track_id:             str
    vehicle_class:        str
    bbox:                 list[float]
    centroid:             tuple[float, float]
    is_stationary:        bool  = False
    stationary_duration_s: float = 0.0
    in_zone_duration_s:   float = 0.0
    speed_kmh:            float = 0.0
    plate_number:         Optional[str]   = None
    plate_confidence:     float = 0.0
    camera_id:            str   = ""


@dataclass
class Zone:
    """
    Enforcement zone loaded from fixtures/zones_pilot.geojson or DB.
    threshold_s is the dwell time before a violation is raised.
    """
    id:          str
    zone_type:   str        # NO_PARKING | BUSWAY_LANE | BICYCLE_LANE | DESIGNATED_STOP
    threshold_s: int  = 30  # configurable per zone (PRD Section 6.3)
    corridor:    str  = ""
    name:        str  = ""
    # Shapely polygon — loaded separately by ZoneManager
    _polygon:    object = field(default=None, repr=False)

    def contains(self, point: tuple[float, float]) -> bool:
        """Point-in-polygon using shapely. Returns False if polygon not loaded."""
        if self._polygon is None:
            logger.warning("Zone %s has no polygon loaded — returning False.", self.id)
            return False
        try:
            from shapely.geometry import Point
            return self._polygon.contains(Point(point))
        except Exception as exc:
            logger.error("contains() failed for zone %s: %s", self.id, exc)
            return False


@dataclass
class ViolationEvent:
    """
    A single detected violation event ready for Kafka / DB persistence.
    All fields mirror the `violations` table schema (PRD Section 12.1).
    """
    id:                   str    = field(default_factory=lambda: str(uuid.uuid4()))
    violation_type:       ViolationType = ViolationType.ILLEGAL_PARKING
    severity:             Severity      = Severity.HIGH
    track_id:             str    = ""
    camera_id:            str    = ""
    zone_id:              str    = ""
    plate_number:         Optional[str] = None
    composite_confidence: float  = 0.0
    timestamp:            datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_s:           float  = 0.0
    vehicle_class:        str    = ""
    status:               str    = "DETECTED"
    legal_basis_code:     Optional[str] = None
    sanction_code:        Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id":                   self.id,
            "violation_type":       self.violation_type.value,
            "severity":             self.severity.value,
            "track_id":             self.track_id,
            "camera_id":            self.camera_id,
            "zone_id":              self.zone_id,
            "plate_number":         self.plate_number,
            "composite_confidence": self.composite_confidence,
            "timestamp":            self.timestamp.isoformat(),
            "duration_s":           self.duration_s,
            "vehicle_class":        self.vehicle_class,
            "status":               self.status,
            "legal_basis_code":     self.legal_basis_code,
            "sanction_code":        self.sanction_code,
        }


# --------------------------------------------------------------------------- #
# Legal Reference lookup (FR-LEGAL-01) — deterministic YAML-backed
# --------------------------------------------------------------------------- #
class LegalReferenceService:
    """
    Deterministic lookup from legal_reference/violation_legal_map.yaml.
    Never uses an LLM for legal decisions (PRD FR-LEGAL-01).
    """

    def __init__(self, yaml_path: str = "legal_reference/violation_legal_map.yaml"):
        self._map: dict = {}
        self._load(yaml_path)

    def _load(self, path: str):
        try:
            import yaml
            from pathlib import Path
            text = Path(path).read_text(encoding="utf-8")
            self._map = yaml.safe_load(text) or {}
            logger.info("Legal reference map loaded from %s (%d entries)", path, len(self._map))
        except Exception as exc:
            logger.warning("Could not load legal reference map (%s). Lookups will return empty.", exc)

    def get(self, violation_type: str) -> dict:
        return self._map.get(violation_type, {})

    def legal_basis(self, violation_type: str) -> Optional[str]:
        return self.get(violation_type).get("legal_basis_code")

    def sanction_code(self, violation_type: str) -> Optional[str]:
        return self.get(violation_type).get("sanction_code")


# Singleton instance — loaded once at import time
_legal_service: Optional[LegalReferenceService] = None


def get_legal_service() -> LegalReferenceService:
    global _legal_service
    if _legal_service is None:
        _legal_service = LegalReferenceService()
    return _legal_service


# --------------------------------------------------------------------------- #
# Violation Rule Engine
# --------------------------------------------------------------------------- #
class ViolationRuleEngine:
    """
    Deterministic rule engine — PRD Section 6.3.

    Each rule fires when the track's state + zone type + duration threshold
    match the configured conditions. No probabilities; fully auditable.

    All rules are intentionally kept simple to ensure legal explainability.
    """

    def __init__(self, legal_service: Optional[LegalReferenceService] = None):
        self._legal = legal_service or get_legal_service()

    def _make_event(
        self,
        track: VehicleTrack,
        zone: Zone,
        vtype: ViolationType,
        severity: Severity,
        duration_s: float,
    ) -> ViolationEvent:
        """Helper: stamp legal basis from YAML fixture onto the violation event."""
        vt_str = vtype.value
        return ViolationEvent(
            violation_type       = vtype,
            severity             = severity,
            track_id             = track.track_id,
            camera_id            = track.camera_id,
            zone_id              = zone.id,
            plate_number         = track.plate_number,
            composite_confidence = track.plate_confidence,
            duration_s           = duration_s,
            vehicle_class        = track.vehicle_class,
            legal_basis_code     = self._legal.legal_basis(vt_str),
            sanction_code        = self._legal.sanction_code(vt_str),
        )

    # ---------------------------------------------------------------------- #
    # Main evaluation entry point
    # ---------------------------------------------------------------------- #
    def evaluate(self, track: VehicleTrack, zone: Zone) -> Optional[ViolationEvent]:
        """
        Returns a ViolationEvent if the rule fires for this track+zone pair,
        else returns None.

        Called once per (track, zone) pair per frame tick.
        """
        if zone.zone_type == "NO_PARKING":
            return self._rule_no_parking(track, zone)

        elif zone.zone_type == "BUSWAY_LANE":
            return self._rule_busway(track, zone)

        elif zone.zone_type == "BICYCLE_LANE":
            return self._rule_bicycle_lane(track, zone)

        elif zone.zone_type == "DESIGNATED_STOP":
            return self._rule_illegal_dropoff(track, zone)

        return None

    # ---------------------------------------------------------------------- #
    # Individual rules
    # ---------------------------------------------------------------------- #
    def _rule_no_parking(self, track: VehicleTrack, zone: Zone) -> Optional[ViolationEvent]:
        """
        ILLEGAL_PARKING: vehicle is stationary in a NO_PARKING zone for >= threshold_s.
        All vehicle classes that can park (car, motorcycle, truck, bus, angkot, bajaj).
        """
        PARKING_CLASSES = {"car", "motorcycle", "truck", "bus", "angkot", "bajaj"}
        if track.vehicle_class not in PARKING_CLASSES:
            return None
        if track.is_stationary and track.stationary_duration_s >= zone.threshold_s:
            return self._make_event(
                track, zone,
                ViolationType.ILLEGAL_PARKING, Severity.HIGH,
                track.stationary_duration_s,
            )
        return None

    def _rule_busway(self, track: VehicleTrack, zone: Zone) -> Optional[ViolationEvent]:
        """
        BUSWAY_VIOLATION: any vehicle except a Transjakarta bus enters the busway lane.
        Fires immediately (threshold_s == 0 — any presence is a violation).
        """
        BUSWAY_ALLOWED = {"transjakarta_bus"}  # only official BRT buses are permitted
        if track.vehicle_class in BUSWAY_ALLOWED:
            return None
        # Any motorised vehicle in the busway lane is a violation
        MOTORISED = {"car", "motorcycle", "truck", "bus", "angkot", "bajaj"}
        if track.vehicle_class in MOTORISED:
            return self._make_event(
                track, zone,
                ViolationType.BUSWAY_VIOLATION, Severity.CRITICAL,
                track.in_zone_duration_s,
            )
        return None

    def _rule_bicycle_lane(self, track: VehicleTrack, zone: Zone) -> Optional[ViolationEvent]:
        """
        BICYCLE_LANE_VIOLATION: motorised vehicle in bicycle lane for >= threshold_s.
        Bicycles and pedestrians are exempt.
        """
        MOTORISED = {"car", "motorcycle", "truck", "bus", "angkot", "bajaj"}
        if track.vehicle_class not in MOTORISED:
            return None
        if track.in_zone_duration_s >= zone.threshold_s:
            return self._make_event(
                track, zone,
                ViolationType.BICYCLE_LANE_VIOLATION, Severity.HIGH,
                track.in_zone_duration_s,
            )
        return None

    def _rule_illegal_dropoff(self, track: VehicleTrack, zone: Zone) -> Optional[ViolationEvent]:
        """
        ILLEGAL_DROPOFF: public transport (angkot, bus) is stationary OUTSIDE a
        designated stop for >= 15 s (PM Perhubungan 15/2019).
        """
        PUBLIC_TRANSPORT = {"angkot", "bus"}
        if track.vehicle_class not in PUBLIC_TRANSPORT:
            return None
        if not track.is_stationary:
            return None
        # Must be OUTSIDE the designated stop polygon
        if zone.contains(track.centroid):
            return None  # inside the stop — legal
        if track.stationary_duration_s >= 15:
            return self._make_event(
                track, zone,
                ViolationType.ILLEGAL_DROPOFF, Severity.MEDIUM,
                track.stationary_duration_s,
            )
        return None

    # ---------------------------------------------------------------------- #
    # Ganjil-Genap (future-only — not wired in v1 demo)
    # ---------------------------------------------------------------------- #
    def check_ganjil_genap(
        self,
        plate: str,
        corridor: str,
        dt: datetime,
        holiday_dates: list[str],
    ) -> Optional[ViolationEvent]:
        """
        Future-only. ANPR confidence must be >= 0.92 before calling (caller's
        responsibility). Do not wire into the v1 demo flow.
        """
        import re as _re
        RESTRICTED_CORRIDORS = {
            "SUDIRMAN", "THAMRIN", "GATOT_SUBROTO",
            "HR_RASUNA_SAID", "SIMATUPANG",
        }
        RESTRICTED_HOURS = [(6, 10), (16, 21)]   # Pergub DKI 155/2018

        if corridor.upper() not in RESTRICTED_CORRIDORS:
            return None
        date_str = dt.strftime("%Y-%m-%d")
        if dt.weekday() >= 5 or date_str in holiday_dates:
            return None
        in_window = any(start <= dt.hour < end for start, end in RESTRICTED_HOURS)
        if not in_window:
            return None

        match = _re.search(r'\d+', plate.replace(" ", ""))
        if not match:
            return None
        last_digit = int(match.group()[-1])
        is_even_plate = (last_digit % 2 == 0)
        is_even_day   = (dt.day % 2 == 0)

        if is_even_plate != is_even_day:
            return ViolationEvent(
                violation_type       = ViolationType.GANJIL_GENAP,
                severity             = Severity.HIGH,
                plate_number         = plate,
                duration_s           = 0,
                legal_basis_code     = self._legal.legal_basis("GANJIL_GENAP"),
                sanction_code        = self._legal.sanction_code("GANJIL_GENAP"),
            )
        return None
