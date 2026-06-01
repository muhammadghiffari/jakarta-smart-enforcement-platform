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
DETECTION_MODEL          = os.getenv("DETECTION_MODEL", "yolo11n.pt").strip()
PLATE_MODEL              = os.getenv("PLATE_MODEL", "models/plate_detector_best.pt").strip()
CONFIDENCE_THRESHOLD     = float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.45"))
PLATE_CONFIDENCE         = float(os.getenv("PLATE_CONFIDENCE_THRESHOLD", "0.50"))

# 8 vehicle classes — PRD Section 11.2
VEHICLE_CLASSES = [
    "car", "motorcycle", "truck", "bus",
    "angkot", "bajaj", "bicycle", "pedestrian"
]

# Minimum plate crop size in pixels — PRD FR-ANPR-01
MIN_PLATE_W = 32
MIN_PLATE_H = 16


def _load_yolo(model_path: str, fallback: Optional[str] = None):
    """Load YOLO model with optional fallback (PRD RULE-07)."""
    from ultralytics import YOLO
    try:
        logger.info("Loading model: %s", model_path)
        m = YOLO(model_path)
        logger.info("Loaded: %s", model_path)
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

    def __init__(self, model_path: str = DETECTION_MODEL):
        self.model = _load_yolo(model_path, fallback="yolo11n.pt")
        self.conf  = CONFIDENCE_THRESHOLD

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
        results = self.model(frame, conf=self.conf, verbose=False)
        detections = []
        allowed_vehicles = {"car", "motorcycle", "truck", "bus", "angkot", "bajaj", "bicycle"}
        for r in results:
            names = r.names  # may differ if using COCO pretrained model
            for box in r.boxes:
                cls_id   = int(box.cls[0])
                cls_name = names.get(cls_id, VEHICLE_CLASSES[cls_id] if cls_id < len(VEHICLE_CLASSES) else str(cls_id)).lower()
                
                # Normalize motorbike to motorcycle
                if cls_name == "motorbike":
                    cls_name = "motorcycle"
                
                # Only keep vehicles
                if cls_name not in allowed_vehicles:
                    continue
                
                detections.append({
                    "bbox":       box.xyxy[0].tolist(),   # [x1, y1, x2, y2]
                    "class_id":   cls_id,
                    "class_name": cls_name,
                    "confidence": float(box.conf[0]),
                })
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

    def __init__(self, model_path: str = PLATE_MODEL):
        # Graceful fallback to a generic model if custom weights not found
        if not Path(model_path).exists():
            logger.warning(
                "Plate model not found at %s. Using yolo11n.pt as fallback. "
                "Re-export from Kaggle to get best accuracy.",
                model_path
            )
            model_path = "yolo11n.pt"
        self.model = _load_yolo(model_path)
        self.conf  = PLATE_CONFIDENCE

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
        results = self.model(frame, conf=self.conf, verbose=False)
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
