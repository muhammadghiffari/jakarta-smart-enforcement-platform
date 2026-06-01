# services/api/app/routers/inference.py
from __future__ import annotations

import base64
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.ai_pipeline.detector import PlateDetector, VehicleDetector

router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


class ImageInferenceRequest(BaseModel):
    image_base64: str = Field(..., description="JPEG/PNG as base64 or data URL")
    run_plate_detection: bool = False


class DetectionResponse(BaseModel):
    source: dict[str, Any]
    model: dict[str, Any]
    elapsed_ms: int
    image_width: int
    image_height: int
    detections: list[dict[str, Any]]
    annotated_image: str


def _model_path(env_name: str, fallback: str) -> str:
    return os.getenv(env_name, fallback).strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ultralytics_demo_image() -> Path | None:
    try:
        import ultralytics

        candidate = Path(ultralytics.__file__).resolve().parent / "assets" / "bus.jpg"
        return candidate if candidate.exists() else None
    except Exception:
        return None


def _decode_image(image_base64: str) -> np.ndarray:
    payload = image_base64.split(",", 1)[1] if "," in image_base64[:80] else image_base64
    try:
        raw = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image payload") from exc

    arr = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Image could not be decoded")
    return frame


def _encode_jpeg(frame: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise HTTPException(status_code=500, detail="Annotated image encoding failed")
    encoded = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


@lru_cache(maxsize=1)
def _vehicle_detector() -> VehicleDetector:
    return VehicleDetector(_model_path("DETECTION_MODEL", "models/yolo26n.pt"))


@lru_cache(maxsize=1)
def _plate_detector() -> PlateDetector:
    return PlateDetector(_model_path("PLATE_MODEL", "models/plate_detector_best.pt"))


def _draw_detections(frame: np.ndarray, detections: list[dict[str, Any]]) -> np.ndarray:
    out = frame.copy()
    for detection in detections:
        x1, y1, x2, y2 = [int(value) for value in detection["bbox"]]
        color = (204, 102, 0)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"{detection['class_name']} {detection['confidence']:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(out, (x1, max(0, y1 - th - 9)), (x1 + tw + 8, y1), color, -1)
        cv2.putText(out, label, (x1 + 4, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        for plate in detection.get("plates", []):
            px1, py1, px2, py2 = [int(value) for value in plate["bbox"]]
            cv2.rectangle(out, (px1, py1), (px2, py2), (41, 151, 255), 2)
    return out


def _source_descriptor(kind: str, path: Path | None = None) -> dict[str, Any]:
    if kind == "demo" and path is not None:
        return {
            "type": "bundled_sample",
            "name": "Ultralytics traffic sample",
            "path": str(path),
            "note": "Bundled local image used to prove the detector path without external network cameras.",
        }
    return {
        "type": "uploaded_frame",
        "name": "Operator uploaded frame",
        "path": None,
        "note": "Image selected in the dashboard and sent to the local inference API.",
    }


def _run_inference(frame: np.ndarray, run_plate_detection: bool, source: dict[str, Any]) -> DetectionResponse:
    started = time.perf_counter()
    vehicle_detector = _vehicle_detector()
    raw_detections = vehicle_detector.detect(frame)

    detections: list[dict[str, Any]] = []
    plate_detector = _plate_detector() if run_plate_detection else None
    for index, item in enumerate(raw_detections):
        detection = {
            "id": f"det-{index + 1}",
            "bbox": [round(float(value), 2) for value in item["bbox"]],
            "class_id": int(item["class_id"]),
            "class_name": str(item["class_name"]),
            "confidence": round(float(item["confidence"]), 4),
            "plates": [],
        }

        if plate_detector is not None:
            plates = plate_detector.detect_in_vehicle_crop(item["bbox"], frame)
            detection["plates"] = [
                {
                    "bbox": [int(value) for value in plate["bbox"]],
                    "confidence": round(float(plate["confidence"]), 4),
                }
                for plate in plates
            ]

        detections.append(detection)

    annotated = _draw_detections(frame, detections)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    height, width = frame.shape[:2]
    vehicle_path = _model_path("DETECTION_MODEL", "models/yolo26n.pt")
    plate_path = _model_path("PLATE_MODEL", "models/plate_detector_best.pt")

    return DetectionResponse(
        source=source,
        model={
            "vehicle_model": vehicle_path,
            "vehicle_model_exists": Path(vehicle_path).exists(),
            "plate_model": plate_path,
            "plate_model_exists": Path(plate_path).exists(),
            "plate_detection": run_plate_detection,
        },
        elapsed_ms=elapsed_ms,
        image_width=width,
        image_height=height,
        detections=detections,
        annotated_image=_encode_jpeg(annotated),
    )


@router.get("/model")
def model_status():
    vehicle_path = _model_path("DETECTION_MODEL", "models/yolo26n.pt")
    plate_path = _model_path("PLATE_MODEL", "models/plate_detector_best.pt")
    demo_source = _ultralytics_demo_image() or (_repo_root() / "demo.jpg")
    return {
        "sources": [
            _source_descriptor("demo", demo_source),
            _source_descriptor("upload"),
        ],
        "vehicle_model": vehicle_path,
        "vehicle_model_exists": Path(vehicle_path).exists(),
        "vehicle_loaded": _vehicle_detector.cache_info().currsize > 0,
        "plate_model": plate_path,
        "plate_model_exists": Path(plate_path).exists(),
        "plate_loaded": _plate_detector.cache_info().currsize > 0,
    }


@router.post("/image", response_model=DetectionResponse)
def infer_image(req: ImageInferenceRequest):
    frame = _decode_image(req.image_base64)
    return _run_inference(frame, req.run_plate_detection, _source_descriptor("upload"))


@router.post("/demo", response_model=DetectionResponse)
def infer_demo(run_plate_detection: bool = False):
    sample = _ultralytics_demo_image() or (_repo_root() / "demo.jpg")
    frame = cv2.imread(str(sample))
    if frame is None:
        raise HTTPException(status_code=404, detail=f"Demo image not readable: {sample}")
    return _run_inference(frame, run_plate_detection, _source_descriptor("demo", sample))
