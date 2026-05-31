#!/usr/bin/env python3
"""
scripts/run_pipeline.py
JSEP end-to-end inference test — vehicle + plate detection on image or video.

Usage examples:
  # Run on the demo grey image (no real detections expected)
  python scripts/run_pipeline.py --source demo.jpg

  # Run on a real photo or video clip
  python scripts/run_pipeline.py --source path/to/traffic.jpg
  python scripts/run_pipeline.py --source path/to/clip.mp4

  # Show live annotated window (requires GUI / X11)
  python scripts/run_pipeline.py --source demo.mp4 --show

  # Skip ANPR (faster, just vehicle detection + rules)
  python scripts/run_pipeline.py --source demo.jpg --no-anpr

  # Use a specific vehicle model instead of the DETECTION_MODEL env var
  python scripts/run_pipeline.py --source demo.jpg --vehicle-model yolo11n.pt
"""

import argparse
import json
import logging
import sys
import requests
from pathlib import Path

# ── repo root on sys.path so local imports work ──────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

from services.ai_pipeline.pipeline import JSEPPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("run_pipeline")


def parse_args():
    p = argparse.ArgumentParser(description="JSEP inference pipeline runner")
    p.add_argument("--source",         required=True,       help="Image/video path, RTSP URL, or webcam index (0)")
    p.add_argument("--vehicle-model",  default=None,        help="Override DETECTION_MODEL env var")
    p.add_argument("--plate-model",    default=None,        help="Override PLATE_MODEL env var")
    p.add_argument("--zone-path",      default="fixtures/zones_pilot.geojson")
    p.add_argument("--legal-yaml",     default="legal_reference/violation_legal_map.yaml")
    p.add_argument("--show",           action="store_true", help="Display annotated frames with cv2.imshow")
    p.add_argument("--no-save",        action="store_true", help="Do not save annotated output")
    p.add_argument("--no-anpr",        action="store_true", help="Skip ANPR stage (faster)")
    p.add_argument("--max-frames",     type=int, default=0, help="Limit to N frames (0 = all)")
    p.add_argument("--summary-out",    default=None,        help="Path to write JSON summary (optional)")
    return p.parse_args()


def main():
    args = parse_args()

    logger.info("═" * 60)
    logger.info("JSEP Pipeline — source: %s", args.source)
    logger.info("  Vehicle model : %s", args.vehicle_model or "(from DETECTION_MODEL env)")
    logger.info("  Plate model   : %s", args.plate_model   or "(from PLATE_MODEL env)")
    logger.info("  ANPR          : %s", "disabled" if args.no_anpr else "enabled")
    logger.info("  Zone file     : %s", args.zone_path)
    logger.info("  Save output   : %s", not args.no_save)
    logger.info("═" * 60)

    pipeline = JSEPPipeline(
        vehicle_model = args.vehicle_model,
        plate_model   = args.plate_model,
        zone_path     = args.zone_path,
        legal_yaml    = args.legal_yaml,
        run_anpr      = not args.no_anpr,
    )

    frame_count = 0
    total_violations = 0

    for result in pipeline.run(
        source = args.source,
        show   = args.show,
        save   = not args.no_save,
    ):
        frame_count    += 1
        viol_this_frame = len(result.get("violations", []))
        total_violations += viol_this_frame
        tracks           = result.get("tracks", [])

        if viol_this_frame > 0 or frame_count == 1 or (frame_count % 50 == 0):
            logger.info(
                "Frame %d | tracks=%d | violations_this_frame=%d | total=%d",
                frame_count, len(tracks), viol_this_frame, total_violations,
            )

        for v in result.get("violations", []):
            logger.warning(
                "  ⚠  %s | track=#%s | plate=%s | duration=%.1fs | legal=%s",
                v.violation_type.value,
                v.track_id,
                v.plate_number or "unknown",
                v.duration_s,
                v.legal_basis_code or "n/a",
            )
            # Push live to FastAPI WebSocket Webhook
            try:
                payload = {
                    "id": str(v.id),
                    "camera_id": "CAM-DEMO-01",
                    "track_id": str(v.track_id),
                    "violation_type": v.violation_type.value,
                    "zone_id": None,
                    "vehicle_class": v.vehicle_class,
                    "start_time": v.timestamp.isoformat(),
                    "end_time": None,
                    "duration_seconds": int(v.duration_s),
                    "status": "DETECTED",
                    "composite_confidence": float(v.composite_confidence) if hasattr(v, 'composite_confidence') else 0.85
                }
                requests.post("http://localhost:8000/api/v1/violations/internal/event", json=payload, timeout=2.0)
            except Exception as e:
                logger.error("Failed to push to API: %s", e)

        if args.max_frames and frame_count >= args.max_frames:
            logger.info("Reached max_frames=%d, stopping.", args.max_frames)
            break

    # ── Summary ──────────────────────────────────────────────────────────────
    summary = pipeline.summary()
    summary["frames_processed"] = frame_count

    logger.info("═" * 60)
    logger.info("Pipeline complete.")
    logger.info("  Frames processed : %d", frame_count)
    logger.info("  Total violations : %d", summary["total_violations"])
    if summary["by_type"]:
        for vtype, count in summary["by_type"].items():
            logger.info("    %-35s %d", vtype, count)
    logger.info("═" * 60)

    if args.summary_out:
        out_path = Path(args.summary_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        logger.info("Summary written to %s", args.summary_out)

    return 0 if summary["total_violations"] >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
