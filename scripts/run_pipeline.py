#!/usr/bin/env python3
"""
scripts/run_pipeline.py
JSEP end-to-end inference — vehicle + plate detection on image/video/RTSP.

All 4 model files in models/ are used:
  - vehicle_detection_best.pt  → primary vehicle detector (VehicleDetector)
  - yolo26n.pt                 → fallback vehicle detector if primary missing
  - plate_detector_best.pt     → primary plate detector (PlateDetector / ANPR Stage 1)
  - yolo26s.pt                 → fallback plate detector if primary missing

Usage examples
--------------
  # Real video, GPU auto-detected, show live window
  python scripts/run_pipeline.py --source data/videos/cctv.mp4 --show

  # Loop video infinitely (great for demo kiosk)
  python scripts/run_pipeline.py --source data/videos/cctv.mp4 --loop --show

  # Live RTSP stream
  python scripts/run_pipeline.py --source rtsp://admin:pass@192.168.1.100:554/stream

  # Force CPU (even if CUDA is available)
  python scripts/run_pipeline.py --source data/videos/cctv.mp4 --device cpu

  # Force GPU 0
  python scripts/run_pipeline.py --source data/videos/cctv.mp4 --device cuda:0

  # Skip ANPR (faster, just vehicle detection + violation rules)
  python scripts/run_pipeline.py --source data/videos/cctv.mp4 --no-anpr

  # Webcam
  python scripts/run_pipeline.py --source 0 --show
"""

import argparse
import json
import logging
import sys
import requests
from pathlib import Path

# ── repo root on sys.path so local imports work ────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

from services.ai_pipeline.pipeline import JSEPPipeline
from services.ai_pipeline.detector import DETECTION_MODEL, PLATE_MODEL, JSEP_DEVICE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("run_pipeline")


MODELS_DIR = ROOT / "models"

# ── All 4 model paths ──────────────────────────────────────────────────────────
MODEL_VEHICLE_PRIMARY  = str(MODELS_DIR / "yolov8m.pt")
MODEL_VEHICLE_FALLBACK = None
MODEL_PLATE_PRIMARY    = str(MODELS_DIR / "plate_detector_best.pt")
MODEL_PLATE_FALLBACK   = str(MODELS_DIR / "yolo26s.pt")


def _resolve_vehicle_model(override: str | None) -> str:
    if override:
        return override
    if Path(MODEL_VEHICLE_PRIMARY).exists():
        return MODEL_VEHICLE_PRIMARY
    logger.warning("vehicle_detection_best.pt not found — using yolo26n.pt fallback")
    return MODEL_VEHICLE_FALLBACK


def _resolve_plate_model(override: str | None) -> str:
    if override:
        return override
    if Path(MODEL_PLATE_PRIMARY).exists():
        return MODEL_PLATE_PRIMARY
    if Path(MODEL_PLATE_FALLBACK).exists():
        logger.warning("plate_detector_best.pt not found — using yolo26s.pt fallback")
        return MODEL_PLATE_FALLBACK
    return MODEL_VEHICLE_FALLBACK   # last resort: yolo26n


def parse_args():
    p = argparse.ArgumentParser(
        description="JSEP real-time inference pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--source",          required=True,
                   help="Video file path, RTSP/HLS URL, or webcam index (0)")
    p.add_argument("--vehicle-model",   default=None,
                   help="Override vehicle detection model path (default: vehicle_detection_best.pt)")
    p.add_argument("--plate-model",     default=None,
                   help="Override plate detection model path (default: plate_detector_best.pt)")
    p.add_argument("--device",          default=None,
                   help="Inference device: 'cuda:0', 'cuda:1', 'cpu' (default: auto-detect GPU)")
    p.add_argument("--zone-path",       default="fixtures/zones_pilot.geojson",
                   help="Path to GeoJSON zone file")
    p.add_argument("--legal-yaml",      default="legal_reference/violation_legal_map.yaml",
                   help="Path to legal reference YAML")
    p.add_argument("--show",            action="store_true",
                   help="Display annotated frames in a live window (requires GUI)")
    p.add_argument("--loop",            action="store_true",
                   help="Loop video file infinitely (ignored for RTSP streams)")
    p.add_argument("--no-save",         action="store_true",
                   help="Do not write annotated output to runs/pipeline/")
    p.add_argument("--no-anpr",         action="store_true",
                   help="Skip ANPR stage (faster, vehicle detection + rules only)")
    p.add_argument("--max-frames",      type=int, default=0,
                   help="Stop after N frames (0 = unlimited)")
    p.add_argument("--summary-out",     default=None,
                   help="Write JSON summary to this path when done")
    p.add_argument("--api-url",         default="http://localhost:8000",
                   help="Base URL of the JSEP FastAPI backend for live event push")
    return p.parse_args()


def main():
    args = parse_args()

    vehicle_model = _resolve_vehicle_model(args.vehicle_model)
    plate_model   = _resolve_plate_model(args.plate_model)
    device        = args.device or JSEP_DEVICE

    # ── Startup banner ────────────────────────────────────────────────────────
    logger.info("═" * 65)
    logger.info("JSEP Real-Time Inference Pipeline")
    logger.info("  Source          : %s", args.source)
    logger.info("  Device          : %s", device)
    logger.info("  ANPR            : %s", "DISABLED (--no-anpr)" if args.no_anpr else "ENABLED")
    logger.info("  Loop            : %s", "YES (Ctrl+C or Q to stop)" if args.loop else "NO")
    logger.info("")
    logger.info("  Models loaded:")
    logger.info("    [Vehicle]  %s  %s",
                "✓" if Path(vehicle_model).exists() else "✗ (MISSING!)", vehicle_model)
    logger.info("    [Plate]    %s  %s",
                "✓" if Path(plate_model).exists()  else "✗ (MISSING!)", plate_model)
    if MODEL_VEHICLE_FALLBACK:
        logger.info("      [Fallback-V] %s  %s",
            "✓" if Path(MODEL_VEHICLE_FALLBACK).exists() else "✗", MODEL_VEHICLE_FALLBACK)
    if MODEL_PLATE_FALLBACK:
        logger.info("      [Fallback-P] %s  %s",
            "✓" if Path(MODEL_PLATE_FALLBACK).exists() else "✗", MODEL_PLATE_FALLBACK)
    logger.info("  Zone file       : %s", args.zone_path)
    logger.info("  API push        : %s/api/v1/violations/internal/event", args.api_url)
    logger.info("═" * 65)

    # ── Build pipeline ────────────────────────────────────────────────────────
    pipeline = JSEPPipeline(
        vehicle_model = vehicle_model,
        plate_model   = plate_model,
        zone_path     = args.zone_path,
        legal_yaml    = args.legal_yaml,
        run_anpr      = not args.no_anpr,
        device        = device,
    )

    frame_count      = 0
    total_violations = 0
    api_push_url     = f"{args.api_url}/api/v1/violations/internal/event"

    # ── Main loop ─────────────────────────────────────────────────────────────
    for result in pipeline.run(
        source = args.source,
        show   = args.show,
        save   = not args.no_save,
        loop   = args.loop,
    ):
        frame_count     += 1
        viol_this_frame  = len(result.get("violations", []))
        total_violations += viol_this_frame
        tracks           = result.get("tracks", [])
        fps_actual       = result.get("fps_actual", 0)
        loop_count       = result.get("loop_count", 0)

        # Progress log every 50 frames, or whenever a violation fires
        if viol_this_frame > 0 or frame_count == 1 or (frame_count % 50 == 0):
            loop_tag = f" [loop {loop_count}]" if loop_count else ""
            logger.info(
                "Frame %d%s | fps=%.1f | tracks=%d | violations=%d (total=%d)",
                frame_count, loop_tag, fps_actual,
                len(tracks), viol_this_frame, total_violations,
            )

        # Log each violation and push to API
        for v in result.get("violations", []):
            logger.warning(
                "  ⚠  %s | class=%s | track=#%s | plate=%s | duration=%.1fs | conf=%.2f | legal=%s",
                v.violation_type.value,
                v.vehicle_class,
                v.track_id,
                v.plate_number or "unknown",
                v.duration_s,
                v.composite_confidence,
                v.legal_basis_code or "n/a",
            )

            # Push real violation event to FastAPI → dashboard WebSocket
            try:
                payload = {
                    "id":                   str(v.id),
                    "camera_id":            "CAM-LIVE-01",
                    "track_id":             str(v.track_id),
                    "violation_type":       v.violation_type.value,
                    "zone_id":              None,
                    "vehicle_class":        v.vehicle_class,
                    "start_time":           v.timestamp.isoformat(),
                    "end_time":             None,
                    "duration_seconds":     int(v.duration_s),
                    "status":               "DETECTED",
                    "composite_confidence": float(v.composite_confidence),
                }
                resp = requests.post(api_push_url, json=payload, timeout=2.0)
                if resp.status_code != 200:
                    logger.warning("API push returned %d: %s", resp.status_code, resp.text[:100])
            except requests.exceptions.ConnectionError:
                pass  # API server not running — pipeline still works standalone
            except Exception as e:
                logger.error("Failed to push event to API: %s", e)

        if args.max_frames and frame_count >= args.max_frames:
            logger.info("Reached max_frames=%d — stopping.", args.max_frames)
            break

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = pipeline.summary()
    summary["frames_processed"] = frame_count

    logger.info("═" * 65)
    logger.info("Pipeline complete.")
    logger.info("  Frames processed : %d", frame_count)
    logger.info("  Total violations : %d", summary["total_violations"])
    if summary["by_type"]:
        for vtype, count in summary["by_type"].items():
            logger.info("    %-40s %d", vtype, count)
    logger.info("═" * 65)

    if args.summary_out:
        out_path = Path(args.summary_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        logger.info("Summary written to %s", args.summary_out)

    return 0 if summary["total_violations"] >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
