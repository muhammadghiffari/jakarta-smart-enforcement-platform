# services/ai_pipeline/pipeline.py
# JSEP end-to-end pipeline orchestrator
# Accepts: image path | video path | numpy frame | RTSP/HLS URL
# Outputs: per-frame list of ViolationEvents + annotated frames
#
# Processing flow per frame:
#   VehicleDetector → JSEPTracker → PlateDetector (per vehicle) → ANPRPipeline → ViolationRuleEngine

import cv2
import time
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Generator, Optional

import numpy as np

from .detector       import VehicleDetector, PlateDetector, detect_vehicles_and_plates, DETECTION_MODEL, PLATE_MODEL, DISPLAY_LABEL
from .tracker        import JSEPTracker
from .violation_rules import (
    VehicleTrack, Zone, ViolationEvent,
    ViolationRuleEngine, LegalReferenceService,
)

# ANPR pipeline is in ml/ — import relative to repo root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.anpr_pipeline import ANPRPipeline

logger = logging.getLogger("jsep.pipeline")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
STATIONARY_SPEED_KMH_THRESHOLD = 3.0    # below this speed → considered stationary
PIXELS_PER_METER               = 10.0   # rough calibration for speed estimate
FPS_DEFAULT                    = 25.0   # assumed fps when reading from file
SAVE_OUTPUT                    = os.getenv("SAVE_PIPELINE_OUTPUT", "true").lower() == "true"
OUTPUT_DIR                     = Path(os.getenv("PIPELINE_OUTPUT_DIR", "runs/pipeline"))
ANPR_EVERY_N_FRAMES            = int(os.getenv("ANPR_EVERY_N_FRAMES", "5"))  # run OCR only every N frames


# --------------------------------------------------------------------------- #
# Track state manager (stationary duration, zone dwell time)
# --------------------------------------------------------------------------- #
class TrackStateManager:
    """
    Maintains per-track temporal state between frames:
      - stationary duration (seconds)
      - zone dwell duration (seconds)
      - centroid history for speed estimation
      - plate crop history for cross-frame ANPR
    """

    def __init__(self, fps: float = FPS_DEFAULT):
        self.fps         = fps
        self._state: dict[int, dict] = {}

    def update(self, track_id: int, centroid: tuple[float, float], in_zone: bool) -> dict:
        dt = 1.0 / self.fps
        s = self._state.setdefault(track_id, {
            "stationary_s":     0.0,
            "zone_s":           0.0,
            "prev_centroid":    centroid,
            "speed_kmh":        0.0,
            "plate_crops":      [],
        })

        # Speed estimate from centroid displacement
        dx = centroid[0] - s["prev_centroid"][0]
        dy = centroid[1] - s["prev_centroid"][1]
        pixel_dist = (dx**2 + dy**2) ** 0.5
        meters     = pixel_dist / PIXELS_PER_METER
        speed_kmh  = (meters / dt) * 3.6
        s["prev_centroid"] = centroid
        s["speed_kmh"]     = speed_kmh

        # Stationary counter
        if speed_kmh < STATIONARY_SPEED_KMH_THRESHOLD:
            s["stationary_s"] += dt
        else:
            s["stationary_s"] = 0.0

        # Zone dwell counter
        if in_zone:
            s["zone_s"] += dt
        else:
            s["zone_s"] = 0.0

        return s

    def add_plate_crop(self, track_id: int, crop: np.ndarray, max_history: int = 5):
        s = self._state.get(track_id, {})
        crops = s.get("plate_crops", [])
        crops.append(crop)
        if len(crops) > max_history:
            crops.pop(0)
        s["plate_crops"] = crops
        self._state[track_id] = s

    def get_plate_crops(self, track_id: int) -> list[np.ndarray]:
        return self._state.get(track_id, {}).get("plate_crops", [])

    def remove(self, track_id: int):
        self._state.pop(track_id, None)


# --------------------------------------------------------------------------- #
# Zone manager — loads from GeoJSON fixture
# --------------------------------------------------------------------------- #
class ZoneManager:
    """
    Loads enforcement zones from fixtures/zones_pilot.geojson and provides
    fast point-in-polygon lookup (shapely).
    """

    def __init__(self, geojson_path: str = "fixtures/zones_pilot.geojson"):
        self.zones: list[Zone] = []
        self._load(geojson_path)

    def _load(self, path: str):
        import json
        try:
            from shapely.geometry import shape
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                geom  = shape(feat["geometry"])
                self.zones.append(Zone(
                    id          = props.get("name", str(len(self.zones))),
                    zone_type   = props.get("zone_type", "NO_PARKING"),
                    threshold_s = int(props.get("threshold_s", 30)),
                    corridor    = props.get("corridor", ""),
                    name        = props.get("name", ""),
                    _polygon    = geom,
                ))
            logger.info("Loaded %d enforcement zones from %s", len(self.zones), path)
        except FileNotFoundError:
            logger.warning("Zone GeoJSON not found at %s. No zones will be enforced.", path)
        except Exception as exc:
            logger.error("Zone loading failed: %s", exc)

    def zones_containing(self, point: tuple[float, float]) -> list[Zone]:
        """Return all zones whose polygon contains the given (x, y) centroid."""
        return [z for z in self.zones if z.contains(point)]


# --------------------------------------------------------------------------- #
# Annotator — draw boxes and labels on frames
# --------------------------------------------------------------------------- #
class FrameAnnotator:
    COLORS = {
        "car":         (  0, 200,   0),
        "motorcycle":  (  0, 165, 255),
        "truck":       (255,   0,   0),
        "bus":         (255, 128,   0),
        "angkot":      (  0, 255, 255),
        "bajaj":       (128,   0, 255),
        "bicycle":     (255, 255,   0),
        "pedestrian":  (200, 200, 200),
        "plate":       (  0,   0, 255),
        "violation":   (  0,   0, 200),
    }

    @classmethod
    def draw(
        cls,
        frame: np.ndarray,
        tracks: list[dict],
        plates: list[dict],
        anpr_results: dict[int, dict],
        violations: list[ViolationEvent],
    ) -> np.ndarray:
        out = frame.copy()
        violation_track_ids = {v.track_id for v in violations}

        # ── Draw plate boxes from full-frame detection ──────────────────────────
        for p in plates:
            px1, py1, px2, py2 = map(int, p["bbox"])
            cv2.rectangle(out, (px1, py1), (px2, py2), (0, 0, 255), 2)
            plate_label = f"plate {p['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(plate_label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            cv2.rectangle(out, (px1, py2), (px1 + tw, py2 + th + 4), (0, 0, 200), -1)
            cv2.putText(out, plate_label, (px1, py2 + th + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

        # ── Draw vehicle tracks ─────────────────────────────────────────────────
        for t in tracks:
            x1, y1, x2, y2 = map(int, t["bbox"])
            track_id = t["track_id"]
            cls_name = t.get("class_name", "vehicle")
            color    = cls.COLORS.get(cls_name, (0, 200, 0))

            if str(track_id) in violation_track_ids or track_id in violation_track_ids:
                color = cls.COLORS["violation"]
                cv2.rectangle(out, (x1-2, y1-2), (x2+2, y2+2), (0, 0, 200), 3)

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

            label = f"#{track_id} {DISPLAY_LABEL.get(cls_name, cls_name)} {t['confidence']:.2f}"
            anpr  = anpr_results.get(track_id)
            if anpr and anpr.get("plate_cleaned"):
                plate_str = anpr["plate_cleaned"]
                conf_str  = f"{anpr['composite_confidence']:.2f}"
                label += f" | {plate_str} ({conf_str})"
                if anpr.get("needs_human_review"):
                    label += " [REVIEW]"

            # Background for label readability
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(out, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Overlay violation alerts at top
        for i, v in enumerate(violations):
            alert = (f"VIOLATION: {v.violation_type.value} | "
                     f"Track #{v.track_id} | {v.vehicle_class} | "
                     f"{v.duration_s:.1f}s | {v.legal_basis_code or ''}")
            cv2.putText(out, alert, (10, 30 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)

        return out


# --------------------------------------------------------------------------- #
# Main Pipeline
# --------------------------------------------------------------------------- #
class JSEPPipeline:
    """
    End-to-end JSEP inference pipeline.

    Supports images, videos, RTSP/HLS URLs, and webcam indices.
    Emits ViolationEvents and annotated frames.

    Usage (quick test)
    ------------------
    pipeline = JSEPPipeline()
    for frame_result in pipeline.run("demo.mp4"):
        print(frame_result["violations"])
    """

    def __init__(
        self,
        vehicle_model: Optional[str] = None,
        plate_model:   Optional[str] = None,
        zone_path:     str = "fixtures/zones_pilot.geojson",
        legal_yaml:    str = "legal_reference/violation_legal_map.yaml",
        fps_override:  Optional[float] = None,
        run_anpr:      bool = True,
        device:        Optional[str] = None,   # e.g. "cuda:0", "cpu" — auto-detected if None
    ):
        from .detector import JSEP_DEVICE
        resolved_device = device or JSEP_DEVICE

        # Use DETECTION_MODEL from detector.py env config (yolov8m.pt by default)
        self.vehicle_detector = VehicleDetector(
            vehicle_model or os.getenv("DETECTION_MODEL", DETECTION_MODEL),
            device=resolved_device,
        )
        self.plate_detector   = PlateDetector(
            plate_model or os.getenv("PLATE_MODEL", PLATE_MODEL),
            device=resolved_device,
        )
        self.tracker          = JSEPTracker()
        self.anpr             = ANPRPipeline() if run_anpr else None
        self.zone_manager     = ZoneManager(zone_path)
        self.rule_engine      = ViolationRuleEngine(LegalReferenceService(legal_yaml))
        self.track_state      = TrackStateManager()
        self.annotator        = FrameAnnotator()
        self.fps_override     = fps_override
        self.run_anpr         = run_anpr
        self.all_violations: list[ViolationEvent] = []
        self._frame_count     = 0  # for ANPR throttling
        logger.info("JSEPPipeline initialised | device=%s | anpr=%s | anpr_every=%d frames",
                    resolved_device, run_anpr, ANPR_EVERY_N_FRAMES)

    # ---------------------------------------------------------------------- #
    # Per-frame processing
    # ---------------------------------------------------------------------- #
    def process_frame(self, frame: np.ndarray, fps: float) -> dict:
        """
        Process a single BGR frame.

        Returns
        -------
        dict with keys:
          tracks     : list[dict]            — tracked vehicles
          anpr       : dict[int, dict]       — ANPR results keyed by track_id
          violations : list[ViolationEvent]  — events raised this frame
          frame_out  : np.ndarray            — annotated frame
        """
        self.track_state.fps = fps
        self._frame_count += 1
        run_anpr_this_frame = (self._frame_count == 1) or (self._frame_count % ANPR_EVERY_N_FRAMES == 0)

        # ─── Stage 1: detect vehicles ──────────────────────────────────────────
        raw_detections = self.vehicle_detector.detect(frame)
        tracks = self.tracker.update(raw_detections, frame)

        # ─── Stage 2: detect plates on FULL FRAME (not per-vehicle crop) ───────
        # This ensures no plate is missed due to vehicle crop misalignment.
        full_frame_plates = self.plate_detector.detect_plates(frame, return_crops=True)

        anpr_results: dict = {}
        frame_violations: list[ViolationEvent] = []

        # ─── Stage 3–8 (ANPR, throttled) + Zone checks per track ───────────────
        for t in tracks:
            x1, y1, x2, y2 = map(int, t["bbox"])
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            centroid = (cx, cy)
            tid = t["track_id"]

            # Find matching zones
            matched_zones = self.zone_manager.zones_containing(centroid)
            in_zone = len(matched_zones) > 0

            # Update track state (duration, speed)
            state = self.track_state.update(tid, centroid, in_zone)

            # ANPR (throttled): find the best plate crop overlapping this vehicle bbox
            if self.run_anpr and self.anpr and run_anpr_this_frame:
                # Match plate detections that overlap with this vehicle's bounding box
                best_plate = None
                best_iou   = 0.0
                for p in full_frame_plates:
                    px1, py1, px2, py2 = p["bbox"]
                    # Compute IoU / overlap between vehicle bbox and plate bbox
                    ix1 = max(x1, px1); iy1 = max(y1, py1)
                    ix2 = min(x2, px2); iy2 = min(y2, py2)
                    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                    if inter > 0:
                        # Plate must be mostly inside the vehicle box
                        plate_area = (px2 - px1) * (py2 - py1)
                        overlap_ratio = inter / (plate_area + 1e-6)
                        if overlap_ratio > 0.3 and p["confidence"] > best_iou:
                            best_iou   = p["confidence"]
                            best_plate = p

                if best_plate and best_plate.get("crop") is not None:
                    self.track_state.add_plate_crop(tid, best_plate["crop"])
                    prior_crops = self.track_state.get_plate_crops(tid)[:-1]
                    anpr_result = self.anpr.process(best_plate["crop"], cross_frame_crops=prior_crops)
                    anpr_results[tid] = anpr_result

            # Build VehicleTrack for rule engine
            anpr_data = anpr_results.get(tid, {})
            vehicle_track = VehicleTrack(
                track_id              = str(tid),
                vehicle_class         = t.get("class_name", "car"),
                bbox                  = t["bbox"],
                centroid              = centroid,
                is_stationary         = state["stationary_s"] > 0,
                stationary_duration_s = state["stationary_s"],
                in_zone_duration_s    = state["zone_s"],
                speed_kmh             = state["speed_kmh"],
                plate_number          = anpr_data.get("plate_cleaned"),
                plate_confidence      = anpr_data.get("composite_confidence", 0.0),
            )

            # Evaluate violation rules
            for zone in matched_zones:
                event = self.rule_engine.evaluate(vehicle_track, zone)
                if event:
                    event.track_id = str(tid)
                    frame_violations.append(event)
                    self.all_violations.append(event)
                    logger.info(
                        "VIOLATION: %s | track=%s | plate=%s | duration=%.1fs | zone=%s",
                        event.violation_type.value,
                        tid,
                        event.plate_number,
                        event.duration_s,
                        zone.name,
                    )

        # Annotate frame — draw plate boxes AND vehicle tracks
        frame_out = self.annotator.draw(frame, tracks, full_frame_plates, anpr_results, frame_violations)

        return {
            "tracks":     tracks,
            "plates":     full_frame_plates,
            "anpr":       anpr_results,
            "violations": frame_violations,
            "frame_out":  frame_out,
        }

    # ---------------------------------------------------------------------- #
    # Video / Image runner
    # ---------------------------------------------------------------------- #
    def run(self, source, show: bool = False, save: bool = SAVE_OUTPUT, loop: bool = False) -> Generator[dict, None, None]:
        """
        Generator — yields per-frame result dicts.

        Parameters
        ----------
        source : str | int | Path
          - Path to image (.jpg/.png) → processes one frame
          - Path to video (.mp4/.avi/…) → processes all frames
          - RTSP/HLS URL string → streams until interrupted
          - int (0) → webcam
        show   : display annotated frames with cv2.imshow
        save   : write annotated output to runs/pipeline/
        loop   : if True, restart video file from frame 0 when it ends (no effect on RTSP streams)
        """
        source = str(source)

        # Image shortcut
        if Path(source).is_file() and Path(source).suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
            frame = cv2.imread(source)
            if frame is None:
                raise ValueError(f"Could not read image: {source}")
            result = self.process_frame(frame, fps=1.0)
            if save:
                self._save_frame(result["frame_out"], source, frame_idx=0)
            if show:
                cv2.imshow("JSEP", result["frame_out"])
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            yield result
            return

        is_file_source = Path(source).is_file() if not source.isdigit() else False

        def _open_cap():
            return cv2.VideoCapture(source if not source.isdigit() else int(source))

        cap = _open_cap()
        if not cap.isOpened():
            raise ValueError(f"Could not open video source: {source}")

        fps = self.fps_override or cap.get(cv2.CAP_PROP_FPS) or FPS_DEFAULT
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        # Output writer setup
        writer = None
        if save:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = OUTPUT_DIR / f"{Path(source).stem}_jsep.mp4"
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
            logger.info("Saving annotated video to %s", out_path)

        frame_idx  = 0
        loop_count = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    if loop and is_file_source:
                        # Rewind video to beginning
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        loop_count += 1
                        logger.info("Video loop #%d — rewinding to frame 0", loop_count)
                        ret, frame = cap.read()
                        if not ret:
                            break  # truly unreadable
                    else:
                        break

                t0 = time.perf_counter()
                result = self.process_frame(frame, fps)
                elapsed = time.perf_counter() - t0

                result["frame_idx"]   = frame_idx
                result["fps_actual"]  = 1.0 / elapsed if elapsed > 0 else 0
                result["total_frames"]= total_frames
                result["loop_count"]  = loop_count

                if writer:
                    writer.write(result["frame_out"])
                if show:
                    cv2.imshow("JSEP Pipeline", result["frame_out"])
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        logger.info("User pressed Q — stopping pipeline.")
                        break

                yield result
                frame_idx += 1

        except KeyboardInterrupt:
            logger.info("Pipeline interrupted by user.")
        finally:
            cap.release()
            if writer:
                writer.release()
            if show:
                cv2.destroyAllWindows()

    # ---------------------------------------------------------------------- #
    # Helpers
    # ---------------------------------------------------------------------- #
    def _save_frame(self, frame: np.ndarray, source: str, frame_idx: int):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stem = Path(source).stem
        out  = OUTPUT_DIR / f"{stem}_frame{frame_idx:04d}_jsep.jpg"
        cv2.imwrite(str(out), frame)
        logger.info("Saved annotated frame to %s", out)

    def summary(self) -> dict:
        """Return a summary of all violations detected in this run."""
        by_type: dict[str, int] = {}
        for v in self.all_violations:
            by_type[v.violation_type.value] = by_type.get(v.violation_type.value, 0) + 1
        return {
            "total_violations":    len(self.all_violations),
            "by_type":             by_type,
            "violations":          [v.to_dict() for v in self.all_violations],
        }
