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

from services.ai_pipeline.pipeline import JSEPPipeline

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


@lru_cache(maxsize=2)
def _jsep_pipeline(run_plate_detection: bool) -> JSEPPipeline:
    vehicle_path = _model_path("DETECTION_MODEL", "models/vehicle_detector_best.pt")
    plate_path = _model_path("PLATE_MODEL", "models/plate_detector_best.pt")
    return JSEPPipeline(
        vehicle_model=vehicle_path,
        plate_model=plate_path,
        run_anpr=run_plate_detection
    )


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
    
    pipeline = _jsep_pipeline(run_plate_detection)
    result = pipeline.process_frame(frame, fps=25.0)

    detections: list[dict[str, Any]] = []
    for t in result["tracks"]:
        track_id = t["track_id"]
        detection = {
            "id": f"track-{track_id}",
            "bbox": [round(float(value), 2) for value in t["bbox"]],
            "class_id": int(t.get("class_id", 0)),
            "class_name": str(t.get("class_name", "vehicle")),
            "confidence": round(float(t.get("confidence", 1.0)), 4),
            "plates": [],
        }

        anpr = result["anpr"].get(track_id)
        if anpr:
            detection["plates"].append({
                "bbox": [0,0,0,0], # Bbox omitted by pipeline wrapper
                "confidence": anpr.get("composite_confidence", 0.0),
                "text": anpr.get("plate_cleaned", ""),
            })

        detections.append(detection)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    height, width = frame.shape[:2]
    vehicle_path = _model_path("DETECTION_MODEL", "models/vehicle_detector_best.pt")
    plate_path = _model_path("PLATE_MODEL", "models/plate_detector_best.pt")

    return DetectionResponse(
        source=source,
        model={
            "vehicle_model": vehicle_path,
            "vehicle_model_exists": Path(vehicle_path).exists(),
            "plate_model": plate_path,
            "plate_model_exists": Path(plate_path).exists(),
            "plate_detection": run_plate_detection,
            "full_pipeline_active": True,
            "violations_detected": len(result["violations"])
        },
        elapsed_ms=elapsed_ms,
        image_width=width,
        image_height=height,
        detections=detections,
        annotated_image=_encode_jpeg(result["frame_out"]),
    )


@router.get("/model")
def model_status():
    vehicle_path = _model_path("DETECTION_MODEL", "models/vehicle_detector_best.pt")
    plate_path = _model_path("PLATE_MODEL", "models/plate_detector_best.pt")
    demo_source = _ultralytics_demo_image() or (_repo_root() / "demo.jpg")
    return {
        "sources": [
            _source_descriptor("demo", demo_source),
            _source_descriptor("upload"),
        ],
        "vehicle_model": vehicle_path,
        "vehicle_model_exists": Path(vehicle_path).exists(),
        "vehicle_loaded": _jsep_pipeline.cache_info().currsize > 0,
        "plate_model": plate_path,
        "plate_model_exists": Path(plate_path).exists(),
        "plate_loaded": _jsep_pipeline.cache_info().currsize > 0,
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

