# ml/anpr_pipeline.py
# JSEP 8-stage ANPR pipeline — PRD Section 6.2
#
# Stage 1 : Plate detection          (PlateDetector — injected)
# Stage 2 : Quality assessment       (resolution + blur score)
# Stage 3 : Super-resolution         (Real-ESRGAN ×4 if quality < 0.6)
# Stage 4 : Deskew / perspective     (contour-based angle correction)
# Stage 5 : OCR                      (EasyOCR primary / PaddleOCR CPU fallback)
# Stage 6 : Regex validation         (Indonesian plate patterns)
# Stage 7 : Composite confidence     (0.6·ocr + 0.3·format + 0.1·cross-frame)
# Stage 8 : Human review gate        (composite < 0.75 → human_review queue)

import re
import logging
import numpy as np

logger = logging.getLogger("jsep.anpr")

# --------------------------------------------------------------------------- #
# Stage 6 — Indonesian plate regex patterns
# --------------------------------------------------------------------------- #
PLATE_STANDARD   = r'^[A-Z]{1,2}\s?\d{1,4}\s?[A-Z]{1,3}$'
PLATE_GOVERNMENT = r'^(RI\s?\d+|[A-Z]{2}\s?\d{1,4}\s?[A-Z]{0,3})$'
PLATE_MILITARY   = r'^(TNI|POLRI|[A-Z])\s?\d{1,5}$'
PLATE_DIPLOMATIC = r'^CD\s?\d{1,4}(\s?\d{1,4})?$'
PLATE_PATTERNS   = [PLATE_STANDARD, PLATE_GOVERNMENT, PLATE_MILITARY, PLATE_DIPLOMATIC]

# Common OCR error corrections for Indonesian plates
OCR_CORRECTIONS = {
    "0": "O", "1": "I", "5": "S",
    "О": "O",  # Cyrillic O → Latin O
}


def _apply_ocr_corrections(text: str) -> str:
    """Heuristic correction for typical misreads on the letter-only suffix."""
    match = re.match(r'^([A-Z]{1,2}\s?)(\d{1,4})(\s?)(.*)$', text)
    if match:
        prefix, digits, sep, suffix = match.groups()
        corrected_suffix = "".join(OCR_CORRECTIONS.get(c, c) for c in suffix.upper())
        return f"{prefix}{digits}{sep}{corrected_suffix}"
    return text


def validate_plate(ocr_text: str) -> tuple[bool, str]:
    """
    Stage 6: Validate cleaned OCR text against Indonesian plate patterns.

    Returns
    -------
    (is_valid, cleaned_text)
    """
    cleaned = ocr_text.upper().strip().replace("-", "").replace(".", "")
    cleaned = _apply_ocr_corrections(cleaned)
    for pattern in PLATE_PATTERNS:
        if re.match(pattern, cleaned):
            return True, cleaned
    return False, cleaned


# --------------------------------------------------------------------------- #
# Main ANPR pipeline class
# --------------------------------------------------------------------------- #
class ANPRPipeline:
    """
    Stages 2–8 of the 8-stage ANPR pipeline.
    Stage 1 (plate detection) is handled by PlateDetector and injected as crops.

    OCR Engine Priority:
    1. PaddleOCR CPU mode  (PP-OCRv5, highest accuracy — same model weights as GPU)
    2. EasyOCR             (GPU-accelerated, stable fallback on WSL)
    3. Returns empty string (graceful degradation)

    Usage
    -----
    pipeline = ANPRPipeline()
    result   = pipeline.process(plate_crop_bgr)
    """

    def __init__(self):
        self._init_ocr()
        self._init_super_resolution()

    # ---------------------------------------------------------------------- #
    # Initialisation
    # ---------------------------------------------------------------------- #
    def _init_ocr(self):
        """Stage 5: PaddleOCR CPU primary (best accuracy), EasyOCR fallback."""
        self.ocr = None
        self.ocr_backend = None
        self.ocr_available = False

        # ── Priority 1: EasyOCR (GPU Accelerated) ─────────────────────────
        try:
            import easyocr
            self.ocr = easyocr.Reader(
                ["en"],
                gpu=True,       # uses GPU if available, silently falls back to CPU
                verbose=False,
            )
            self.ocr_backend = "easyocr"
            self.ocr_available = True
            logger.info("EasyOCR (GPU) initialised successfully.")
            return
        except Exception as exc:
            logger.warning("EasyOCR not available (%s). Falling back to PaddleOCR…", exc)

        # ── Priority 2: PaddleOCR (PP-OCRv5) CPU Fallback ─────────────────
        # paddlepaddle 3.0.0 CPU-only build is installed (no CUDA).
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(lang="en")
            self.ocr_backend = "paddleocr"
            self.ocr_available = True
            logger.info("PaddleOCR CPU fallback initialised.")
            return
        except Exception as exc:
            logger.warning("PaddleOCR also failed (%s). OCR disabled.", exc)

        logger.error("No OCR backend available — ANPR will return empty strings.")

    def _init_super_resolution(self):
        """Stage 3: Real-ESRGAN ×4 super-resolution."""
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
            model = RRDBNet(num_in_ch=3, num_out_ch=3, scale=4, num_feat=64)
            self.upsampler = RealESRGANer(
                scale=4,
                model_path="weights/RealESRGAN_x4plus.pth",
                model=model,
                half=False,
            )
            self.sr_available = True
            logger.info("Real-ESRGAN super-resolution loaded.")
        except Exception as exc:
            logger.info("Real-ESRGAN not available (%s). Stage 3 will be skipped.", exc)
            self.upsampler  = None
            self.sr_available = False

    # ---------------------------------------------------------------------- #
    # Stage 2 — Quality assessment
    # ---------------------------------------------------------------------- #
    def assess_quality(self, crop: np.ndarray) -> float:
        """
        Returns quality score 0.0–1.0 based on:
          - Resolution score: how close W/H is to recommended 120×40 px
          - Sharpness (Laplacian variance): detects motion blur
        """
        import cv2
        h, w = crop.shape[:2]
        resolution_score = min(w / 120.0, 1.0) * min(h / 40.0, 1.0)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 500.0, 1.0)
        return round(0.5 * resolution_score + 0.5 * sharpness_score, 3)

    # ---------------------------------------------------------------------- #
    # Stage 3 — Super-resolution
    # ---------------------------------------------------------------------- #
    def super_resolve(self, crop: np.ndarray, quality_score: float) -> np.ndarray:
        """Apply Real-ESRGAN ×4 upscale when quality < 0.6 (PRD Stage 3)."""
        if quality_score < 0.6 and self.sr_available:
            try:
                output, _ = self.upsampler.enhance(crop, outscale=4)
                return output
            except Exception as exc:
                logger.debug("Super-resolution failed: %s", exc)
        return crop

    # ---------------------------------------------------------------------- #
    # Stage 4 — Deskew
    # ---------------------------------------------------------------------- #
    def deskew(self, crop: np.ndarray) -> np.ndarray:
        """Perspective correction via contour detection and minAreaRect."""
        import cv2
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return crop
        largest = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(largest)
        angle = rect[2]
        if abs(angle) > 30:
            return crop
        center = (crop.shape[1] // 2, crop.shape[0] // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(crop, M, (crop.shape[1], crop.shape[0]))

    # ---------------------------------------------------------------------- #
    # Stage 5 — OCR
    # ---------------------------------------------------------------------- #
    def run_ocr(self, crop: np.ndarray) -> tuple[str, float]:
        """
        Dispatches to the best available OCR backend.
        Returns (raw_text, mean_confidence).
        """
        if not self.ocr_available or self.ocr is None:
            return "", 0.0

        try:
            if self.ocr_backend == "easyocr":
                return self._run_easyocr(crop)
            elif self.ocr_backend == "paddleocr":
                return self._run_paddleocr(crop)
        except Exception as exc:
            logger.warning("OCR failed: %s", exc)

        return "", 0.0

    def _run_easyocr(self, crop: np.ndarray) -> tuple[str, float]:
        """EasyOCR inference."""
        results = self.ocr.readtext(crop, detail=1, paragraph=False)
        if not results:
            return "", 0.0
        texts, confs = [], []
        for (_, text, conf) in results:
            texts.append(text)
            confs.append(float(conf))
        return " ".join(texts), float(np.mean(confs)) if confs else 0.0

    def _run_paddleocr(self, crop: np.ndarray) -> tuple[str, float]:
        """PaddleOCR inference."""
        # PaddleOCR 3.x ocr() usage without cls
        result = self.ocr.ocr(crop)
        if not result:
            return "", 0.0
        
        res = result[0]
        # PaddleOCR 3.0.0 format
        if isinstance(res, dict) and "rec_texts" in res:
            texts = res.get("rec_texts", [])
            confidences = res.get("rec_scores", [])
        else:
            # PaddleOCR 2.x format fallback
            if not res: return "", 0.0
            texts, confidences = [], []
            for line in res:
                texts.append(line[1][0])
                confidences.append(float(line[1][1]))
                
        return " ".join(texts), float(np.mean(confidences)) if confidences else 0.0

    # ---------------------------------------------------------------------- #
    # Stage 7 — Composite confidence
    # ---------------------------------------------------------------------- #
    @staticmethod
    def compute_composite_confidence(
        ocr_conf: float,
        format_valid: bool,
        cross_frame_texts: list[str],
        ocr_text: str,
    ) -> float:
        """
        composite = 0.6 * ocr_conf + 0.3 * format_score + 0.1 * cross_frame_consistency
        PRD Section 6.2 Stage 7.
        """
        format_score = 1.0 if format_valid else 0.0
        if cross_frame_texts:
            consistency = sum(1 for t in cross_frame_texts if t == ocr_text) / len(cross_frame_texts)
        else:
            consistency = 0.5  # unknown — neutral prior
        composite = 0.6 * ocr_conf + 0.3 * format_score + 0.1 * consistency
        return round(composite, 3)

    # ---------------------------------------------------------------------- #
    # Full pipeline — all 8 stages
    # ---------------------------------------------------------------------- #
    def process(
        self,
        plate_crop: np.ndarray,
        cross_frame_crops: list[np.ndarray] | None = None,
    ) -> dict:
        """
        Run stages 2–8 on a plate crop.

        Parameters
        ----------
        plate_crop         : BGR numpy array of the plate region
        cross_frame_crops  : optional list of prior-frame crops for consistency check

        Returns
        -------
        dict with keys:
          plate_raw           : str  — raw OCR output
          plate_cleaned       : str  — regex-cleaned candidate
          is_valid_format     : bool
          ocr_confidence      : float 0–1
          quality_score       : float 0–1
          composite_confidence: float 0–1
          needs_human_review  : bool  — True when composite < 0.75 (RULE-04)
          rejection_reason    : str | None
          ocr_backend         : str  — which OCR engine was used
        """
        # Stage 2: quality
        quality = self.assess_quality(plate_crop)

        # Stage 3: super-resolution
        enhanced = self.super_resolve(plate_crop, quality)

        # Stage 4: deskew
        deskewed = self.deskew(enhanced)

        # Stage 5: OCR
        raw_text, ocr_conf = self.run_ocr(deskewed)

        # Stage 6: validation
        is_valid, cleaned = validate_plate(raw_text)

        # Cross-frame OCR for consistency
        cross_texts: list[str] = []
        if cross_frame_crops:
            for prior_crop in cross_frame_crops[:3]:
                prior_raw, _ = self.run_ocr(self.deskew(prior_crop))
                _, prior_cleaned = validate_plate(prior_raw)
                cross_texts.append(prior_cleaned)

        # Stage 7: composite confidence
        composite = self.compute_composite_confidence(ocr_conf, is_valid, cross_texts, cleaned)

        return {
            "plate_raw":            raw_text,
            "plate_cleaned":        cleaned,
            "is_valid_format":      is_valid,
            "ocr_confidence":       round(ocr_conf, 3),
            "quality_score":        quality,
            "composite_confidence": composite,
            "needs_human_review":   composite < 0.75,   # Stage 8 — RULE-04
            "rejection_reason":     None if is_valid else "REGEX_REJECTED",
            "ocr_backend":          self.ocr_backend or "none",
        }
