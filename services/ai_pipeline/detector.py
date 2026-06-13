# services/ai_pipeline/detector.py
# JSEP two-stage detector: VehicleDetector (8 classes) → PlateDetector (ANPR stage 1)
# PRD Section 6.1 — YOLO26 primary, YOLOv11 fallback
# Both models controlled by DETECTION_MODEL / PLATE_MODEL env vars

import os
import logging
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger("jsep.detector")

# --------------------------------------------------------------------------- #
# Config from environment (PRD RULE-01)
# --------------------------------------------------------------------------- #
# Resolve paths relative to the repository root (2 levels up from detector.py)
ROOT_DIR = Path(__file__).resolve().parents[2]

DETECTION_MODEL      = os.getenv("DETECTION_MODEL", str(ROOT_DIR / "models" / "vehicle_detection_best.pt")).strip()
PLATE_MODEL          = os.getenv("PLATE_MODEL",     str(ROOT_DIR / "models" / "plate_detector_best.pt")).strip()
CONFIDENCE_THRESHOLD = float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.25"))  # low for Indonesian traffic
PLATE_CONFIDENCE     = float(os.getenv("PLATE_CONFIDENCE_THRESHOLD",     "0.10"))  # low for small plates

# ── GPU device — auto-detect CUDA, fallback to CPU ─────────────────────────
def _auto_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            dev = "cuda:0"
            logger.info("GPU detected: %s — using %s", torch.cuda.get_device_name(0), dev)
            return dev
    except ImportError:
        pass
    logger.info("No CUDA GPU found — running on CPU")
    return "cpu"

JSEP_DEVICE = os.getenv("JSEP_DEVICE", "") or _auto_device()

# ── 8 vehicle classes — PRD Section 11.2 ────────────────────────────────────
VEHICLE_CLASSES = [
    "car", "motorcycle", "truck", "bus",
    "angkot", "bajaj", "bicycle", "pedestrian"
]

# ── Allowed in detection output ───────────────────────────────────────────
# Only include classes likely to appear in Indonesian traffic videos
ALLOWED_VEHICLES = {"car", "motorcycle", "truck", "bus", "bicycle"}

# ── COCO + custom Indonesian → JSEP canonical name map ────────────────────────
COCO_TO_JSEP: dict[str, str] = {
    # COCO English (yolov8m, yolo26s, yolo26n)
    "person":     "pedestrian",
    "bicycle":    "bicycle",
    "car":        "car",
    "motorcycle": "motorcycle",
    "motorbike":  "motorcycle",
    "bus":        "bus",
    "truck":      "truck",
    # Indonesian (vehicle_detection_best.pt, best.pt)
    "mobil":      "car",
    "motor":      "motorcycle",
    # JSEP-specific
    "angkot":     "angkot",
    "bajaj":      "bajaj",
    "transjakarta_bus": "bus",
}

# ── Display labels (Indonesian) shown on annotated video ─────────────────────
DISPLAY_LABEL: dict[str, str] = {
    "car":         "Mobil",
    "motorcycle":  "Motor",
    "truck":       "Truk",
    "bus":         "Bus",
    "angkot":      "Angkot",
    "bajaj":       "Bajaj",
    "bicycle":     "Sepeda",
    "pedestrian":  "Pejalan",
}

# Minimum plate crop size in pixels — PRD FR-ANPR-01
MIN_PLATE_W = 10
MIN_PLATE_H = 10


def _load_yolo(model_path: str, fallback: Optional[str] = None):
    """Load YOLO model with optional fallback (PRD RULE-07)."""
    from ultralytics import YOLO
    try:
        logger.info("Loading model: %s", model_path)
        m = YOLO(model_path)
        # Log what classes this model actually knows — helps debug wrong detections
        if hasattr(m, "names"):
            logger.info("  Model class map: %s", dict(m.names))
        return m
    except Exception as exc:
        if fallback:
            logger.warning("Primary model %r failed (%s). Falling back to %s", model_path, exc, fallback)
            return YOLO(fallback)
        raise


# --------------------------------------------------------------------------- #
# Vehicle Detector
# --------------------------------------------------------------------------- #
class VehicleDetector:
    """
    Stage 1: Detect vehicle bounding boxes and classify into 8 classes.
    PRD Section 6.1, 11.2.

    Works on single frames (np.ndarray) or file paths (str / Path).
    Confidence threshold filters weak detections (FR-DET-07).
    """

    def __init__(self, model_path: str = DETECTION_MODEL, device: str = JSEP_DEVICE):
        # Primary: vehicle_detection_best.pt (Indonesian classes: mobil, motor, bus, truck)
        # Secondary: yolo26s.pt (COCO 80 classes: car, motorcycle, bus, truck)
        self.model_primary   = _load_yolo(model_path)
        secondary_path       = str(ROOT_DIR / "models" / "yolo26s.pt")
        self.model_secondary = _load_yolo(secondary_path) if Path(secondary_path).exists() else None
        self.conf   = CONFIDENCE_THRESHOLD
        self.device = device
        logger.info("VehicleDetector ready | primary=%s | secondary=%s | device=%s | conf≥%.2f",
                    model_path, secondary_path, self.device, self.conf)

    def detect(self, frame) -> list[dict]:
        """
        Parameters
        ----------
        frame : np.ndarray (BGR) | str | Path  — single frame or image path

        Returns
        -------
        list of dicts:
          bbox        : [x1, y1, x2, y2] in pixels
          class_id    : int (0–7)
          class_name  : str  e.g. "car", "bus"
          confidence  : float 0–1
        """
        allowed = ALLOWED_VEHICLES

        def _run_model(model) -> list[dict]:
            results = model(frame, conf=self.conf, verbose=False, device=self.device)
            dets = []
            for r in results:
                names = r.names
                for box in r.boxes:
                    raw_cls_id = int(box.cls[0])
                    raw_name   = names.get(raw_cls_id, str(raw_cls_id)).lower()
                    cls_name   = COCO_TO_JSEP.get(raw_name, raw_name)
                    if cls_name not in allowed:
                        logger.debug("Dropping class id=%d name=%r", raw_cls_id, raw_name)
                        continue
                    
                    # Map to unified JSEP class_id for tracker
                    jsep_cls_id = VEHICLE_CLASSES.index(cls_name) if cls_name in VEHICLE_CLASSES else 0

                    dets.append({
                        "bbox":       box.xyxy[0].tolist(),
                        "class_id":   jsep_cls_id,
                        "class_name": cls_name,
                        "confidence": float(box.conf[0]),
                    })
            return dets

        # Run primary model (Indonesian-trained)
        detections = _run_model(self.model_primary)

        # Run secondary model (COCO yolo26s) to catch vehicles missed by primary
        if self.model_secondary:
            secondary_dets = _run_model(self.model_secondary)
            # Add secondary detections only if not already covered by primary (simple IoU check)
            for sd in secondary_dets:
                sx1, sy1, sx2, sy2 = sd["bbox"]
                covered = False
                for pd in detections:
                    px1, py1, px2, py2 = pd["bbox"]
                    ix1, iy1 = max(sx1, px1), max(sy1, py1)
                    ix2, iy2 = min(sx2, px2), min(sy2, py2)
                    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                    union = (sx2-sx1)*(sy2-sy1) + (px2-px1)*(py2-py1) - inter
                    if union > 0 and (inter / union) > 0.4:
                        covered = True
                        break
                if not covered:
                    detections.append(sd)

        return detections


# --------------------------------------------------------------------------- #
# Plate Detector
# --------------------------------------------------------------------------- #
class PlateDetector:
    """
    Stage 1 of 8-stage ANPR: detect license plate bounding boxes.
    PRD Section 6.2.

    Designed to be called INSIDE vehicle crops (two-stage approach) but
    also works on full frames for speed when vehicle detector is skipped.
    """

    def __init__(self, model_path: str = PLATE_MODEL, device: str = JSEP_DEVICE):
        # Graceful fallback: plate_detector_best.pt → yolo26s.pt (better for ANPR) → yolo26n.pt
        if not Path(model_path).exists():
            fallback_s = str(ROOT_DIR / "models" / "yolo26s.pt")
            fallback_n = str(ROOT_DIR / "models" / "yolo26n.pt")
            fb = fallback_s if Path(fallback_s).exists() else fallback_n
            logger.warning(
                "Plate model not found at %s — using fallback %s", model_path, fb
            )
            model_path = fb
        self.model  = _load_yolo(model_path)
        self.conf   = PLATE_CONFIDENCE
        self.device = device
        logger.info("PlateDetector ready  | model=%s | device=%s | conf≥%.2f",
                    model_path, self.device, self.conf)

    def detect_plates(self, frame, return_crops: bool = True) -> list[dict]:
        """
        Parameters
        ----------
        frame         : np.ndarray (BGR) | str | Path
        return_crops  : bool  — include numpy crop of each plate in output

        Returns
        -------
        list of dicts:
          bbox        : [x1, y1, x2, y2]
          confidence  : float
          crop        : np.ndarray (if return_crops=True and frame is ndarray)
        """
        results = self.model(frame, conf=self.conf, verbose=False, device=self.device)
        plates = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                w, h = x2 - x1, y2 - y1
                if w < MIN_PLATE_W or h < MIN_PLATE_H:
                    logger.debug("Plate crop too small (%dx%d), skipping.", w, h)
                    continue
                entry = {
                    "bbox":       [x1, y1, x2, y2],
                    "confidence": float(box.conf[0]),
                }
                if return_crops and isinstance(frame, np.ndarray):
                    entry["crop"] = frame[y1:y2, x1:x2].copy()
                plates.append(entry)
        return plates

    def detect_in_vehicle_crop(self, vehicle_bbox: list[float], full_frame: np.ndarray) -> list[dict]:
        """
        Crop the vehicle region from full_frame, run plate detection on the crop,
        and remap plate bbox coordinates back to full-frame space.

        Returns plates with bbox in full-frame coordinates.
        """
        x1v, y1v, x2v, y2v = map(int, vehicle_bbox)
        # Safety clamp to frame bounds
        h_frame, w_frame = full_frame.shape[:2]
        x1v, y1v = max(0, x1v), max(0, y1v)
        x2v, y2v = min(w_frame, x2v), min(h_frame, y2v)

        vehicle_crop = full_frame[y1v:y2v, x1v:x2v]
        if vehicle_crop.size == 0:
            return []

        raw_plates = self.detect_plates(vehicle_crop, return_crops=True)

        # Remap coordinates to full-frame space
        remapped = []
        for p in raw_plates:
            px1, py1, px2, py2 = p["bbox"]
            remapped.append({
                "bbox":       [x1v + px1, y1v + py1, x1v + px2, y1v + py2],
                "confidence": p["confidence"],
                "crop":       p.get("crop"),
            })
        return remapped


# --------------------------------------------------------------------------- #
# Convenience: two-stage detect on a single frame
# --------------------------------------------------------------------------- #
def detect_vehicles_and_plates(
    frame: np.ndarray,
    vehicle_detector: VehicleDetector,
    plate_detector: PlateDetector,
) -> list[dict]:
    """
    Run vehicle detection, then plate detection inside each vehicle bbox.

    Returns list of dicts:
      vehicle_bbox   : [x1, y1, x2, y2]
      vehicle_class  : str
      vehicle_conf   : float
      plates         : list[dict]  — each with bbox (full-frame), confidence, crop
    """
    vehicles = vehicle_detector.detect(frame)
    combined = []
    for v in vehicles:
        plates = plate_detector.detect_in_vehicle_crop(v["bbox"], frame)
        combined.append({
            "vehicle_bbox":  v["bbox"],
            "vehicle_class": v["class_name"],
            "vehicle_conf":  v["confidence"],
            "plates":        plates,
        })
    return combined
