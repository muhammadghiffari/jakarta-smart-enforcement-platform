# services/ai_pipeline/tracker.py
# JSEP BoT-SORT vehicle tracker with OSNet ReID — PRD Section 6.4
# Maintains persistent Track IDs across minimum 2-second occlusion.

import logging
from pathlib import Path
from typing import Optional
import numpy as np

# Resolve repo root
ROOT_DIR = Path(__file__).resolve().parents[2]


logger = logging.getLogger("jsep.tracker")

VEHICLE_CLASSES = [
    "car", "motorcycle", "truck", "bus",
    "angkot", "bajaj", "bicycle", "pedestrian"
]


class JSEPTracker:
    """
    BoT-SORT tracker wrapping BoxMOT.
    PRD Section 6.4 — persistent track IDs, ReID via OSNet-x0.25.

    If boxmot is not installed or GPU is unavailable, falls back to a
    lightweight IoU-only tracker so the pipeline still runs on CPU.
    """

    def __init__(self, reid_weights: Optional[str] = None):
        self._has_gpu = self._check_gpu()
        self._tracker  = None
        self._fallback = False
        default_reid = str(ROOT_DIR / "models" / "osnet_x0_25_msmt17.pt")
        self._load_tracker(reid_weights or default_reid)

    # ---------------------------------------------------------------------- #
    # Initialisation
    # ---------------------------------------------------------------------- #
    def _check_gpu(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _load_tracker(self, reid_weights: str):
        try:
            from boxmot.trackers.tracker_zoo import create_tracker
            device = "cuda:0" if self._has_gpu else "cpu"
            self._tracker = create_tracker(
                "botsort",
                reid_weights=Path(reid_weights),
                device=device,
                half=False,
            )
            logger.info("BoT-SORT tracker loaded (device=%s, reid=%s)", device, reid_weights)
        except Exception as exc:
            logger.warning(
                "BoxMOT unavailable (%s). Using IoU-only fallback tracker. "
                "Run: pip install 'boxmot==19.0.0' for ReID support.",
                exc
            )
            self._fallback = True

    # ---------------------------------------------------------------------- #
    # Public API
    # ---------------------------------------------------------------------- #
    def update(self, detections: list[dict], frame: np.ndarray) -> list[dict]:
        """
        Parameters
        ----------
        detections : output from VehicleDetector.detect()
        frame      : current BGR frame (np.ndarray H×W×3)

        Returns
        -------
        list of dicts:
          track_id    : int  — persistent across frames
          bbox        : [x1, y1, x2, y2]
          class_id    : int
          class_name  : str
          confidence  : float
        """
        if not detections:
            return []

        if self._fallback:
            return self._iou_update(detections)

        # BoxMOT expects np.array shape (N, 6): [x1, y1, x2, y2, conf, cls_id]
        det_array = np.array(
            [[*d["bbox"], d["confidence"], d["class_id"]] for d in detections],
            dtype=np.float32,
        )

        try:
            tracks = self._tracker.update(det_array, frame)
        except Exception as exc:
            logger.error("Tracker update failed: %s. Returning raw detections.", exc)
            return [
                {**d, "track_id": -1}
                for d in detections
            ]

        # BoxMOT output columns: x1 y1 x2 y2 track_id conf cls_id det_ind
        results = []
        for t in tracks:
            cls_id = int(t[6]) if len(t) > 6 else 0
            results.append({
                "bbox":       t[:4].tolist(),
                "track_id":   int(t[4]),
                "confidence": float(t[5]),
                "class_id":   cls_id,
                "class_name": (
                    VEHICLE_CLASSES[cls_id]
                    if cls_id < len(VEHICLE_CLASSES)
                    else str(cls_id)
                ),
            })
        return results

    def reset(self):
        """Reset tracker state between clips/cameras."""
        if not self._fallback and self._tracker is not None:
            try:
                self._tracker.reset()
            except Exception:
                default_reid = str(ROOT_DIR / "models" / "osnet_x0_25_msmt17.pt")
                self._load_tracker(default_reid)
        self._iou_state = {}

    # ---------------------------------------------------------------------- #
    # Fallback: simple IoU matching
    # ---------------------------------------------------------------------- #
    def __init_fallback_state(self):
        if not hasattr(self, "_iou_state"):
            self._iou_state  = {}   # track_id → last bbox
            self._next_id    = 1

    @staticmethod
    def _iou(a: list, b: list) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / (area_a + area_b - inter)

    def _iou_update(self, detections: list[dict]) -> list[dict]:
        self.__init_fallback_state()
        IOU_THRESH = 0.35
        matched_ids: dict[int, list] = {}

        for det in detections:
            best_id, best_iou = None, IOU_THRESH
            for tid, prev_bbox in self._iou_state.items():
                score = self._iou(det["bbox"], prev_bbox)
                if score > best_iou:
                    best_iou, best_id = score, tid
            if best_id is None:
                best_id = self._next_id
                self._next_id += 1
            matched_ids[best_id] = det["bbox"]

        self._iou_state = matched_ids

        return [
            {
                **det,
                "track_id": tid,
            }
            for det, tid in zip(detections, matched_ids.keys())
        ]
