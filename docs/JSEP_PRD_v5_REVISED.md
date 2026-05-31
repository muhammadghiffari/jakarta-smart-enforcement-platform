# JSEP PRD v5.1.3 — Jakarta Smart Enforcement Platform
> **AI Open Innovation Challenge 2026 — DISHUB DKI Jakarta — Case 1**  
> Status: **AGENT-READY** | Revised: May 2026 | Supersedes: v4.0.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement & Background](#2-problem-statement--background)
3. [Goals, Objectives & Success Metrics](#3-goals-objectives--success-metrics)
4. [Stakeholders & User Personas](#4-stakeholders--user-personas)
5. [System Overview & Architecture](#5-system-overview--architecture)
6. [AI Model Specifications](#6-ai-model-specifications)
7. [Functional Requirements](#7-functional-requirements)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Technology Stack](#9-technology-stack)
10. [API Specifications](#10-api-specifications)
11. [Data Requirements & Training Pipeline](#11-data-requirements--training-pipeline)
12. [Database Schema](#12-database-schema)
13. [Risk Register](#13-risk-register)
14. [Implementation Roadmap](#14-implementation-roadmap)
15. [Demo Scope (Competition Boundary)](#15-demo-scope-competition-boundary)
16. [Demo Resource Plan](#16-demo-resource-plan)
17. [Future Roadmap (Out of Scope v1)](#17-future-roadmap-out-of-scope-v1)
18. [Open Questions & Assumptions](#18-open-questions--assumptions)
19. [Glossary](#19-glossary)
20. [Appendix](#20-appendix)

---

## 1. Executive Summary

The **Jakarta Smart Enforcement Platform (JSEP)** is an AI-driven intelligent traffic enforcement and behaviour analysis system for Dinas Perhubungan (DISHUB) DKI Jakarta, addressing Case 1 of the AI Open Innovation Challenge 2026.

Jakarta's road network (7,650 km, 13 million registered vehicles) relies heavily on manual officer patrols. JSEP replaces reactive manual oversight with:
- **Automated CCTV-based violation detection** (illegal parking, busway occupancy, bicycle lane violations, illegal public transport pick-up/drop-off)
- **AI-powered license plate recognition (ANPR)** for Indonesian plates
- **Spatial-temporal hotspot analytics** using H3 hexagonal indexing
- **Officer deployment optimization** using MCLP algorithm

### Competition Deliverables Summary

| Deliverable | Component | Demo Feasibility |
|---|---|---|
| **Model** | CCTV violation detection + ANPR + duration tracking + CRM/JAKI report classifier | ✅ Fully trainable |
| **Dashboard** | Spatial-temporal heatmap, behaviour statistics, live feed, integrated violation database | ✅ Functional prototype |
| **Simulator** | Officer placement + E-TLE camera placement + relevant-unit routing recommendation | ✅ Working demo |
| **Executive Summary** | Trial monitoring analysis, daily stakeholder report, public reporting participation summary | ✅ Template-based |

### Competition Focus Guardrails

The competition case is about **traffic enforcement and road-user behaviour analysis**, not a general smart-city platform. JSEP must prioritize:

1. **Core case violations**: illegal parking, busway lane occupancy, bicycle lane occupancy, and public transport pick-up/drop-off outside designated stops.
2. **Evidence-ready identity and duration**: vehicle type, ANPR result, confidence, start/end time, stopping duration, zone, and camera metadata.
3. **Behaviour intelligence**: spatial-temporal hotspot mapping, repeat-location patterns, time-of-day patterns, and officer/E-TLE camera placement recommendations.
4. **CRM/public complaint automation**: classify citizen reports, de-duplicate with CCTV events, corroborate with nearest cameras, and route to the relevant unit.

Features such as Ganjil-Genap, LLM-generated legal narratives, cross-camera ReID, mobile apps, and live government registry lookups are **stretch/future capabilities**. They may be mentioned as roadmap vision, but they must not dominate the prototype narrative.

Important distinction: JSEP **does need legal references, sanction/fine mappings, and rule citations in v1**. Those are implemented as a deterministic legal reference layer, not as LLM/RAG generation. The LLM/RAG component is optional because it drafts prose; it is not required to know which rule, sanction, or report field applies.

### Real End-to-End Prototype Contract

JSEP v1 must be a **working engine**, not a click-through mock. The prototype may use mock adapters only for external government systems that require formal access agreements. Everything that demonstrates AI capability and traffic-enforcement intelligence must run end to end on real or field-captured data.

| Layer | Prototype Requirement | Mock Allowed? |
|---|---|---|
| CCTV ingestion | Ingest real RTSP/HLS streams or recorded real CCTV clips through the same ingestion pipeline | No UI-only playback |
| Vehicle detection | Train/fine-tune and run the detector on real Jakarta/CCTV-domain frames | No hard-coded detections |
| ANPR | Run plate detection + OCR on real plate crops, with confidence and rejection logs | No fixed plate strings except test fixtures |
| Tracking/duration | Compute stationary/in-zone duration from frame timestamps and track state | No prefilled timers |
| Zone logic | Use real/manual GeoJSON polygons over camera views | No fake violation buttons |
| Evidence package | Generate real thumbnail, best frame, video clip, SHA-256 hash, timestamps | No static evidence cards |
| Hotspot analytics | Compute H3 heatmaps from actual generated violation events plus clearly labeled historical/imported data | No hand-painted heatmaps |
| Legal/sanction reference | Deterministic lookup from reviewed fixtures/DB | No LLM as authority |
| CRM/JAKI | Accept real webhook payload shape and process uploaded images/reports; sandbox/local submitter allowed | No static CRM status screen |
| E-TLE/Korlantas/SAMSAT | Mock/stub only until official sandbox/MoU is available | Yes, but visibly labeled |

The presentation should say: **"The AI engine, data pipeline, dashboard, analytics, and reports are real. Only government registry/submission integrations are stubbed because production access requires official agreements."**

### Case Requirement Coverage Matrix

| Competition Requirement | JSEP PRD Coverage | Focus Status |
|---|---|---|
| Detect illegal parking and dedicated-lane violations in real time via CCTV | FR-VIO-01 through FR-VIO-03, Section 6.3 rule engine, dashboard live feed | Core |
| Recognize vehicle identity, vehicle type, and violation duration | ANPR pipeline, vehicle detector classes, tracking/duration state machine, evidence package | Core |
| Map hotspots of negative road-user behaviour | H3 Resolution 10 operator heatmap + Resolution 9 executive rollup, temporal analytics | Core |
| Analyze protocol roads and public-facility areas | Pilot scope covers protocol roads plus station/market areas; zones stored as GeoJSON | Core |
| Handle varying CCTV angles, night, and rain | Camera readiness scoring, augmentation, CLAHE, quality thresholds, human review | Core |
| Integrate and automate CRM/public reports | CRM/JAKI classifier, CCTV corroboration, `crm_reports`, unit dispatch, citizen points | Core |
| Support E-TLE with integrated violation database | Evidence package, E-TLE draft workflow, legal/sanction reference lookup, audit log, human-in-the-loop approval | Core |
| Recommend officer placement or E-TLE camera installation | MCLP optimizer, top uncovered H3 cells, relevant-unit routing matrix | Core |
| Produce daily trial and stakeholder reports | ReportLab executive PDF, KPIs, legal/sanction summaries, public reporting participation metrics | Core |

### Key Impact Targets *(Targets, not verified baselines)*

| Metric | Target |
|---|---|
| Violation Detection Precision | >85% on test dataset |
| ANPR Accuracy (daylight) | >85% on clear plates |
| Alert End-to-End Latency | <3 seconds |
| H3 Hotspot Refresh | Every 15 minutes |
| CRM/JAKI Classification Accuracy | >80% on labeled complaint samples |

---

## 2. Problem Statement & Background

### 2.1 Background

DISHUB DKI Jakarta manages urban transport across the Special Capital Region: 7,650 km of roads, TransJakarta, MRT, LRT, and the JakLingko payment ecosystem. The agency's ATCS (Area Traffic Control System) centrally manages traffic signals.

Traffic violations — particularly illegal parking and dedicated lane occupancy — reduce arterial throughput significantly during peak hours. Current enforcement relies on physical officer presence, which does not scale.

### 2.2 Core Problem

| Pain Point | Detail |
|---|---|
| **Enforcement Gap** | Officer-to-monitored-road-segment ratio is approximately 1:47 |
| **Manual Dependency** | Violations spike within ~15 minutes of officer rotation |
| **Dynamic Hotspots** | Violation clusters are temporal and spatial but not systematically tracked |
| **Data Silos** | CCTV footage, CRM reports, ATCS data, E-TLE records exist in separate systems |
| **Reactive Enforcement** | No predictive capability to pre-position resources |

### 2.3 Violation Types in Scope

| Violation Type | Definition | Duration Threshold |
|---|---|---|
| Illegal Parking (Parkir Liar) | Vehicle stopped/parked in no-parking zone | 30 seconds |
| Busway Lane Occupancy | Non-authorized vehicle in TransJakarta corridor | Immediate (0 seconds) |
| Bicycle Lane Violation | Motorized vehicle in dedicated bicycle infrastructure | 10 seconds |
| Illegal Drop-off/Pick-up | Public transport outside designated stops | 15 seconds |

### 2.4 Opportunity

DISHUB operates extensive CCTV infrastructure across protocol roads and areas around public facilities. This infrastructure is currently used primarily for incident review. JSEP converts this passive asset into an active, intelligence-generating enforcement layer — no new hardware required for most locations.

---

## 3. Goals, Objectives & Success Metrics

### 3.1 Strategic Goals

- **G1**: Automate violation detection to reduce dependence on manual patrol
- **G2**: Generate evidence-grade violation records (photo + plate + timestamp + duration) suitable for E-TLE
- **G3**: Create a data intelligence layer revealing behavioural patterns for proactive enforcement planning
- **G4**: Provide DISHUB command with a real-time operational picture across Jakarta
- **G5**: Increase citizen trust through transparent, consistent enforcement

### 3.2 KPIs

> **Note**: All targets are competition prototype targets. Baselines are from comparable deployments where cited; otherwise marked [TARGET].

| KPI ID | Metric | Target | Baseline Source | Priority |
|---|---|---|---|---|
| KPI-01 | Vehicle Detection mAP50 | >90% on Jakarta test set | [TARGET] | Critical |
| KPI-02 | ANPR Accuracy (daylight) | >85% on clear plates | Comparable Indonesian ANPR systems | Critical |
| KPI-03 | ANPR Accuracy (night/rain) | >68% in adverse conditions | [TARGET, lower bound] | High |
| KPI-04 | Violation Detection Precision | >85% (low false positive) | [TARGET] | Critical |
| KPI-05 | Violation Detection Recall | >78% (acceptable false negative) | [TARGET] | Critical |
| KPI-06 | End-to-End Latency | <3 seconds from event to dashboard | [TARGET] | High |
| KPI-07 | Inference Speed | >20 FPS on NVIDIA Jetson Orin NX 16GB (or cloud GPU for demo) | Jetson Orin NX spec sheet | High |
| KPI-08 | Dashboard Uptime | >99.5% during operational hours | [TARGET] | High |
| KPI-09 | E-TLE Ticket Draft Time | <90 seconds from confirmation | [TARGET] | Medium |
| KPI-10 | Hotspot Refresh Frequency | Every 15 minutes | [TARGET] | Medium |
| KPI-11 | False Alarm Rate | <8% of alerts rejected by human reviewer | [TARGET, conservative for prototype] | Critical |
| KPI-12 | CRM/JAKI Report Classification Accuracy | >80% on labeled complaint samples | [TARGET] | High |
| KPI-13 | CCTV Corroboration Rate for Valid Citizen Reports | >60% in camera-covered pilot zones | [TARGET] | Medium |
| KPI-14 | Public Reporting Participation Lift | +20% verified reports during pilot socialization window | [TARGET] | Medium |

---

## 4. Stakeholders & User Personas

### 4.1 Stakeholder Map

| Stakeholder | Role | Primary Need | JSEP Touchpoint |
|---|---|---|---|
| DISHUB Operations | Primary User | Field supervision, dispatch | Live map, alert feed, officer assignments |
| Traffic Officers (Petugas) | End User | On-ground enforcement | Mobile alert, violation GPS + details |
| E-TLE Unit | Primary User | Ticket issuance | Violation DB, photo evidence, plate data |
| DISHUB Command / Kadishub | Executive Viewer | Strategic oversight | Executive dashboard, daily digest |
| Biro Hukum (Legal) | Stakeholder | Legal defensibility | Audit log, confidence scores, evidence chain |
| Jakarta Smart City (JSC) | Integration Partner | Data sharing | API access, data feeds |
| Citizen / Masyarakat | Indirect Beneficiary | Road safety | CRM reporting channel |

### 4.2 User Personas

**Persona 1 — Pak Ridwan, Operations Center Supervisor (Age 42)**  
Monitors 200+ CCTV feeds manually. Misses ~80% of violations due to attention limits. Pain: alert fatigue from false positives. Need: high-confidence alerts he can act on immediately.

**Persona 2 — Bu Sari, Field Officer (Age 31)**  
Deployed at Sudirman-Thamrin. Receives imprecise verbal dispatch. Often arrives after violator has left. Need: precise GPS coordinates, vehicle description, current status, and patrol routing suggestion.

**Persona 3 — Pak Hendro, Head of E-TLE Unit (Age 49)**  
Current bottleneck: manual review before each ticket. Need: violation record with photo evidence, confirmed plate, duration timestamp, legal classification — ready for one-click approval.

---

## 5. System Overview & Architecture

### 5.1 High-Level Architecture

JSEP is a five-layer architecture. All layers communicate via Apache Kafka event bus for loose coupling, replay capability, and horizontal scalability.

```
┌──────────────────────────────────────────────────────────┐
│  L5 — PRESENTATION: React Dashboard, Officer Dispatch, E-TLE │
├──────────────────────────────────────────────────────────┤
│  L4 — ANALYTICS: H3 Hotspot, MCLP Optimizer, Reports     │
├──────────────────────────────────────────────────────────┤
│  L3 — EVENT BUS: Apache Kafka, Redis State Cache          │
├──────────────────────────────────────────────────────────┤
│  L2 — AI PIPELINE: YOLO26, ANPR, Violation Rules          │
├──────────────────────────────────────────────────────────┤
│  L1 — INGESTION: RTSP/HLS Capture, CRM Webhook, ATCS      │
└──────────────────────────────────────────────────────────┘
```

### 5.2 Architecture Layers

| Layer | Responsibilities | Key Technologies |
|---|---|---|
| L1 — Ingestion | RTSP/HLS stream capture, CRM webhook, ATCS data adapter | FFmpeg, GStreamer, FastAPI |
| L2 — AI Pipeline | Frame extraction, preprocessing, YOLO26 detection, ANPR, violation logic | Python, YOLO26, PaddleOCR 3.5+ / PP-OCRv5, OpenCV 4.x |
| L3 — Event Bus | Violation events, tracking state, alert dispatch, audit logging | Apache Kafka, Redis |
| L4 — Analytics | H3 hotspot computation, MCLP officer optimizer, behaviour mining | PostGIS, TimescaleDB, H3-py, PuLP |
| L5 — Presentation | Live dashboard, officer dispatch view, E-TLE API, executive reports | React 18, MapLibre GL, FastAPI, ReportLab |

### 5.3 Violation Detection Data Flow

```
CCTV (RTSP/HLS)
    │
    ▼
Frame Extractor (5 FPS detection / 25 FPS evidence buffer)
    │
    ▼
Preprocessor: CLAHE + resolution normalization (640×640)
    │
    ▼
YOLO26n Detector → 8 vehicle classes + zone intersection
    │
    ▼
BoxMOT (BoT-SORT + OSNet ReID) → persistent Track IDs
    │
    ▼
Violation Rule Engine → ViolationEvent emitted
    │
    ├──► ANPR Trigger → PaddleOCR 3.5+ / PP-OCRv5 → Composite confidence
    │
    ▼
Evidence Package (type, plate, timestamps, 10s clip, zone)
    │
    ▼
Kafka topic: violations.confirmed
    │
    ├──► Dashboard Consumer (WebSocket → UI <500ms)
    └──► E-TLE Producer (draft ticket generation)
```

### 5.4 Deployment Topology

| Node Type | Components | Location |
|---|---|---|
| Edge Node (per CCTV cluster) | Jetson Orin NX 16GB, YOLO26 inference, BoxMOT, frame buffer | CCTV hub locations |
| Processing Server | NVIDIA A100 or RTX 4090, ANPR, video archival, batch analytics | DISHUB data center / JSC cloud |
| Analytics Server | CPU-optimized, PostGIS, TimescaleDB, H3, MCLP optimizer | DISHUB data center |
| Web Server | Nginx, React SPA, FastAPI, WebSocket broker | Jakarta Smart City cloud |
| Message Broker | Apache Kafka 3-node, 7-day retention, replication factor 3 | DISHUB infrastructure |

> **Demo Note**: For competition prototype, edge and processing collapsed to a single cloud GPU instance (RTX 4090 or equivalent). Latency target relaxes to <5s in cloud-only mode.

---

## 6. AI Model Specifications

### 6.1 Primary Detection Model: YOLO26

JSEP uses **YOLO26** (Ultralytics, released Q1 2026) as its primary object detection backbone.

> **Fallback**: If YOLO26 is unavailable or licensing is blocked, use **YOLOv11** (Ultralytics, stable release). All architecture decisions below apply to both. Model name in code: `DETECTION_MODEL_PATH = os.getenv("DETECTION_MODEL", "yolo26n.pt")` — swap to `yolo11n.pt` with zero other changes.

#### Why YOLO26 (or YOLOv11 fallback)

| Feature | Relevance to JSEP |
|---|---|
| NMS-Free End-to-End | Reduces per-frame latency — critical for real-time enforcement |
| STAL (Small Target Aware Label Assignment) | Indonesian plates at 15–40m CCTV distance are small objects (~32×16px) |
| MuSGD Optimizer | Faster convergence fine-tuning on Jakarta CCTV dataset |
| Native OBB Support | Handles oblique CCTV angles — plates not aligned to frame axis |
| Multi-task Unified | Lane segmentation in same forward pass as vehicle detection |
| TensorRT Export | Required for Jetson Orin deployment |

#### Model Variants

| Variant | Use Case | Latency Target |
|---|---|---|
| `yolo26n.pt` (Nano) | Edge real-time detection — primary stream | <3ms/frame |
| `yolo26s.pt` (Small) | ANPR trigger localization (plate region) | <8ms/frame |
| `yolo26m.pt` (Medium) | Offline batch reprocessing for audit quality | No real-time constraint |

#### Fine-Tuning Strategy (Realistic for Competition)

```
Base weights:  yolo26n pretrained on COCO 2017 (80 classes, 118K images)
Target domain: Jakarta CCTV (Indonesian vehicles, varied angles, day/night)
Target dataset: 10,000 annotated frames (MVP) → 50,000 (full deployment)
Classes (8):   car, motorcycle, truck, bus, angkot, bajaj, bicycle, pedestrian

Training config:
  imgsz:      640 (edge) / 1280 (GPU server batch)
  epochs:     100 (nano) / 150 (small)
  batch:      16 (single RTX 4090) — NOT 4×A100; see Section 16
  optimizer:  MuSGD (YOLO26 default) / SGD (YOLOv11 fallback)
  patience:   20 (early stopping)

Augmentation pipeline (OpenCV-based — see Section 11.3):
  - Rain streak simulation (cv2.addWeighted with synthetic rain mask)
  - Gaussian blur (motion simulation)
  - CLAHE inverse (overexposure)
  - Gamma adjustment 0.1–0.4 (night simulation)
  - JPEG compression artifacts (quality 40–70)
  - Random horizontal flip, rotation ±15°
  - Mosaic augmentation (YOLO native)
```

#### Lane Segmentation Head

A **separate segmentation model** handles zone detection (busway corridor, bicycle lane, no-parking zone). This is **not** a separate YOLO26 head in the same weights file — it is a separate `yolo26s-seg.pt` model for semantic lane segmentation, run once per camera at startup to generate static zone mask overlays. Zone masks are then used as GeoJSON polygon lookups at runtime.

> **Implementation note**: For demo, zones are pre-digitized GeoJSON polygons (manually or from DISHUB GIS). The segmentation model is used to auto-generate zone polygons from CCTV footage where manual GeoJSON is unavailable.

### 6.2 ANPR Engine — Indonesian License Plate Recognition

The ANPR subsystem is the most legally critical component. All design decisions prioritize legal defensibility.

#### ANPR Pipeline (8 Stages)

| Stage | Operation | Notes |
|---|---|---|
| 1 | Plate region detection | `yolo26s.pt` fine-tuned for plate bounding box. Min plate: 32×16px |
| 2 | Quality assessment | Score 0–1: resolution + Laplacian blur variance + angle skew (<30°) |
| 3 | Super-resolution | Real-ESRGAN ×4 if quality score <0.6. GPU server, target <500ms |
| 4 | Perspective correction | Homography via plate corner keypoints → frontal deskew |
| 5 | OCR | PaddleOCR 3.5+ with PP-OCRv5 recognition fine-tune → character string + per-char confidence. PP-OCRv4 remains fallback if v5 compatibility/performance is weaker on cropped plates. |
| 6 | Format validation | Regex (see below). Reject non-conforming → log rejection reason |
| 7 | Confidence scoring | `composite = 0.6*ocr_conf + 0.3*format_score + 0.1*cross_frame_consistency` |
| 8 | Human review queue | composite <0.75 → flagged for human review, NOT auto-submitted to E-TLE |

#### Camera Enforcement Readiness

Not every existing CCTV feed is suitable for E-TLE-grade ANPR. JSEP classifies each camera so weak feeds still contribute to hotspot analytics without over-claiming ticket quality.

| Readiness | Criteria | Allowed Use |
|---|---|---|
| A — Enforcement-grade | Plate crop ≥32×16px, stable view, daylight ANPR confidence ≥0.85 in calibration | E-TLE draft after human review |
| B — Analytics-grade | Vehicle and zone detection reliable, ANPR intermittent or confidence <0.85 | Hotspot mapping, officer dispatch, human review |
| C — Monitoring-only | Low resolution, severe occlusion, poor angle, or frequent stream loss | Behaviour trend only; no E-TLE draft |

Readiness is recalculated during pilot calibration and shown on the dashboard so DISHUB can decide where new E-TLE cameras are worth installing.

#### Indonesian Plate Regex (Extended)

```python
import re

# Standard civilian plate (private, commercial, public transport)
PLATE_STANDARD = r'^[A-Z]{1,2}\s?\d{1,4}\s?[A-Z]{1,3}$'

# Government/Dinas (red plate): RI + number, or ministry codes
PLATE_GOVERNMENT = r'^(RI\s?\d+|[A-Z]{2}\s?\d{1,4}\s?[A-Z]{0,3})$'

# TNI/POLRI: different format (e.g., "R 12345" or "TNI 123")
PLATE_MILITARY = r'^(TNI|POLRI|[A-Z])\s?\d{1,5}$'

# Diplomatic (CD + numeric)
PLATE_DIPLOMATIC = r'^CD\s?\d{1,4}(\s?\d{1,4})?$'

# Electric Vehicle (blue plate — same format as standard, detect by color)
# Color classification in Stage 7 (plate_color: white/yellow/red/blue/green)

PLATE_PATTERNS = [PLATE_STANDARD, PLATE_GOVERNMENT, PLATE_MILITARY, PLATE_DIPLOMATIC]

def validate_plate(ocr_text: str) -> tuple[bool, str]:
    cleaned = ocr_text.upper().strip()
    for pattern in PLATE_PATTERNS:
        if re.match(pattern, cleaned):
            return True, cleaned
    return False, cleaned  # returns cleaned text even if rejected, for logging
```

> **Note**: Plates failing all patterns are logged as `REGEX_REJECTED` with raw OCR output for analysis. High rejection rate on a camera is a signal of OCR or preprocessing failure.

#### Plate Type Support Matrix

| Plate Type | Background | Text | Detected Via |
|---|---|---|---|
| Standard Private | White | Black | ANPR + regex |
| Public Transport | Yellow | Black | ANPR + color classifier |
| Government / Dinas | Red | White | ANPR + color classifier |
| TNI / POLRI | Black | White/Yellow | ANPR + military regex |
| Diplomatic (CD) | White | Black | ANPR + diplomatic regex |
| Electric Vehicle | Blue | Black | ANPR + color classifier |

### 6.3 Violation Detection Rule Engine

Violation logic is a **deterministic rule engine** — not a neural classifier. This is intentional: rule-based logic is legally auditable and explainable in court.

```python
# Pseudocode — implemented in violation_rules.py
class ViolationRuleEngine:

    def evaluate(self, track: VehicleTrack, zone: Zone) -> Optional[ViolationEvent]:
        
        if zone.type == 'NO_PARKING':
            if track.is_stationary and track.stationary_duration_s >= zone.threshold_s:
                return ViolationEvent(type='ILLEGAL_PARKING', severity='HIGH')

        elif zone.type == 'BUSWAY_LANE':
            if track.vehicle_class not in ['transjakarta_bus']:
                # Immediate — no duration threshold
                return ViolationEvent(type='BUSWAY_VIOLATION', severity='CRITICAL')

        elif zone.type == 'BICYCLE_LANE':
            if track.vehicle_class in ['car', 'motorcycle', 'truck']:
                if track.in_zone_duration_s >= zone.threshold_s:  # default 10s
                    return ViolationEvent(type='BICYCLE_LANE_VIOLATION', severity='HIGH')

        elif zone.type == 'DESIGNATED_STOP':
            if track.vehicle_class in ['angkot', 'bus']:
                if track.is_stationary and not zone.contains(track.centroid):
                    if track.stationary_duration_s >= 15:
                        return ViolationEvent(type='ILLEGAL_DROPOFF', severity='MEDIUM')

        return None
```

**Zone Configuration**: Prohibited zones are GeoJSON polygons in the JSEP config layer, overlaid on camera FOV mappings. Ops team can add/modify zones via dashboard without model retraining. Zone thresholds are configurable per zone instance.

### 6.4 Multi-Object Tracking: BoxMOT (BoT-SORT + ReID)

**Library**: BoxMOT v10+ — BoT-SORT with OSNet-x0.25 ReID embeddings (2.2MB model)

**Why BoxMOT over ByteTrack alone**: BoxMOT integrates appearance-based ReID alongside IoU and Kalman-filter motion prediction, enabling:
- Duration measurement across occlusions (vehicle hidden by passing bus, tree)
- Re-identification: same vehicle re-enters frame as same Track ID (prevents double-counting)
- Low-light robustness: maintains tracks when detection confidence drops in night/rain

**Cross-Camera Matching**: Out of scope for competition enforcement. The prototype performs reliable **single-camera** tracking for duration measurement. Cross-camera matching may be explored later using cosine similarity of OSNet embeddings and a pre-configured camera topology graph, but it is not used to issue E-TLE drafts in v1.

### 6.5 Hotspot Mapping: H3 Spatial Analytics

#### H3 Resolution Specification (Competition-Fit)

JSEP uses a **dual-resolution H3 strategy** so the dashboard supports both executive overview and operational placement decisions.

| Resolution | Avg Cell Area | Use Case |
|---|---|---|
| 7 | ~5.16 km² | City-level overview, executive report |
| 8 | ~0.74 km² | District/corridor level |
| **9** | **~0.105 km² (105,333 m²)** | **Executive and corridor-level hotspot overview** |
| **10** | **~0.015 km² (15,048 m²)** | **Operational hotspot dashboard and officer placement default** |
| 11 | ~2,150 m² | Camera/FOV-level drill-down where enough data exists |

> **Corrected from v4**: v4 incorrectly stated Resolution 9 = ~174 m² per cell. The correct value is ~105,333 m² (~0.105 km²). JSEP uses Resolution 10 as the operational default because the competition asks for violation-prone **points**, not only broad districts.

#### Hotspot Algorithm

```python
# hotspot_engine.py — simplified

import h3
from scipy.stats import gaussian_kde
import numpy as np

def compute_hotspots(violations: list[ViolationEvent], resolution: int = 10) -> dict:
    """
    Returns: dict of {h3_index: risk_score}
    """
    # Step 1: Map violations to H3 cells
    cell_events: dict[str, list] = {}
    for v in violations:
        cell = h3.geo_to_h3(v.lat, v.lng, resolution)
        cell_events.setdefault(cell, []).append(v)

    # Step 2: Temporal decay — weight = exp(-0.1 * age_hours)
    now = datetime.utcnow()
    for cell, events in cell_events.items():
        for e in events:
            age_hours = (now - e.timestamp).total_seconds() / 3600
            e.weight = np.exp(-0.1 * age_hours)

    # Step 3: KDE on H3 cell centroids.
    # Production implementation projects WGS84 lat/lng to a metric CRS for Jakarta
    # before KDE. Initial smoothing radius: 300-600m, calibrated during pilot.
    coords = np.array([h3.h3_to_geo(c) for c in cell_events.keys()])
    weights = np.array([sum(e.weight for e in evs) for evs in cell_events.values()])
    kde = gaussian_kde(coords.T, weights=weights, bw_method='scott')
    kde_density = kde(coords.T)

    # Step 4: Composite risk score
    severity_weights = {'CRITICAL': 1.5, 'HIGH': 1.0, 'MEDIUM': 0.6}
    risk_scores = {}
    for i, cell in enumerate(cell_events.keys()):
        recency = np.mean([e.weight for e in cell_events[cell]])
        severity = np.mean([severity_weights.get(e.severity, 1.0) for e in cell_events[cell]])
        risk_scores[cell] = (
            0.5 * kde_density[i] / kde_density.max() +
            0.3 * recency +
            0.2 * min(severity / 1.5, 1.0)
        )

    return risk_scores
```

### 6.6 Officer Placement Optimizer (MCLP)

```python
# optimizer.py — Maximum Coverage Location Problem via PuLP

from pulp import *
import h3

def solve_mclp(
    demand_cells: dict[str, float],   # h3_index → demand weight
    candidate_positions: list[str],    # H3 cells as candidate officer positions
    n_officers: int,
    coverage_radius_km: float = 0.5   # officer covers all H3 cells within this radius
) -> list[str]:
    """
    Returns ordered list of H3 cells for officer placement.
    Optimality guaranteed for n_officers <= 20 (GLPK).
    Greedy approximation (≥63% optimal) for larger N.
    """
    prob = LpProblem("MCLP_Officer_Placement", LpMaximize)

    # Decision variables
    x = {pos: LpVariable(f"x_{pos}", cat='Binary') for pos in candidate_positions}
    y = {cell: LpVariable(f"y_{cell}", cat='Binary') for cell in demand_cells}

    # Objective: maximize covered demand
    prob += lpSum(demand_cells[c] * y[c] for c in demand_cells)

    # Coverage constraint: cell covered if any officer within radius
    for cell in demand_cells:
        covering_officers = [
            pos for pos in candidate_positions
            if h3.point_dist(h3.h3_to_geo(cell), h3.h3_to_geo(pos), unit='km') <= coverage_radius_km
        ]
        if covering_officers:
            prob += y[cell] <= lpSum(x[pos] for pos in covering_officers)

    # Officer count constraint
    prob += lpSum(x.values()) <= n_officers

    prob.solve(GLPK(msg=0))
    return [pos for pos, var in x.items() if value(var) == 1]
```

**Output**: Ordered list of GPS coordinates recommended for officer placement, per shift (morning 06:00–14:00, afternoon 14:00–22:00, night 22:00–06:00).

---

## 7. Functional Requirements

### 7.1 Stream Ingestion & Video Management

| Req ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-VID-01 | RTSP/HLS stream ingestion | Ingest live RTSP or HLS streams from DISHUB/ATCS CCTV cameras. Minimum 50 concurrent streams per processing node. | Critical |
| FR-VID-02 | Adaptive frame extraction | Extract at 5 FPS for detection. Maintain 25 FPS buffer for 60-second rolling evidence window per camera. | Critical |
| FR-VID-03 | Stream health monitoring | Detect dropout within 10 seconds. Alert operator, log disconnect, auto-reconnect with exponential backoff. | High |
| FR-VID-04 | Video evidence archival | Store 10-second clips (±5s around violation event) with immutable SHA-256 hash for evidence chain. | Critical |
| FR-VID-05 | Variable quality handling | Accept 360p–1080p. Normalize to 640×640 for YOLO26. Log source resolution metadata. | High |
| FR-VID-06 | Multi-angle camera support | Support overhead, angled, and ground-level viewpoints. Store camera FOV metadata as GeoJSON polygon. | High |
| FR-VID-07 | Camera readiness scoring | Classify cameras as A enforcement-grade, B analytics-grade, or C monitoring-only based on plate readability, angle, resolution, lighting, and stream stability. | Critical |

### 7.2 Vehicle Detection & Classification

| Req ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-DET-01 | Real-time vehicle detection | YOLO26n inference >20 FPS per stream on Jetson Orin (or cloud GPU for demo). Detect all 8 vehicle classes. | Critical |
| FR-DET-02 | Multi-object tracking | BoxMOT BoT-SORT with OSNet ReID. Maintain single-camera track identity across minimum 2-second occlusion for duration measurement. Cross-camera ReID is future roadmap only. | Critical |
| FR-DET-03 | Zone intersection detection | Real-time intersection of vehicle bounding box with configured GeoJSON zone polygons. | Critical |
| FR-DET-04 | Stationary detection | Classify as stationary when centroid displacement <5px across 10 consecutive frames at 5 FPS (2-second window). | Critical |
| FR-DET-05 | Low-light adaptation | Auto-apply CLAHE preprocessing when mean frame brightness <80 (0–255 scale). | High |
| FR-DET-06 | Rain detection | Binary classifier (ResNet-18, lightweight) on frame patches to detect heavy rain. Adjust confidence thresholds accordingly. | Medium |
| FR-DET-07 | Configurable thresholds | Per-class confidence threshold (default 0.45). Detections below threshold discarded before violation engine. | High |

### 7.3 ANPR — Automatic Number Plate Recognition

| Req ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-ANPR-01 | Plate region detection | YOLO26s fine-tuned for plate bounding box. Minimum plate resolution: 32×16px before processing. | Critical |
| FR-ANPR-02 | Super-resolution | Real-ESRGAN ×4 upscaling for plates with quality score <0.6. GPU server, target <500ms. | High |
| FR-ANPR-03 | OCR execution | PaddleOCR 3.5+ with PP-OCRv5 Indonesian plate fine-tuning; PP-OCRv4 fallback allowed after validation. Return character string + per-character confidence. | Critical |
| FR-ANPR-04 | Format validation | Validate against extended Indonesian plate regex (Section 6.2). Log rejection reason for all failures. | Critical |
| FR-ANPR-05 | Cross-frame consistency | Majority vote across 3 frames during violation window for final plate string. | High |
| FR-ANPR-06 | Confidence scoring | Composite confidence (Section 6.2, Stage 7). Score <0.75 → human review queue. Never auto-submit to E-TLE. | Critical |
| FR-ANPR-07 | Plate color classification | Classify plate background color (white/yellow/red/blue) as proxy for vehicle category. | Medium |

### 7.4 Violation Detection & Event Management

| Req ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-VIO-01 | Illegal parking detection | Vehicle stationary in NO_PARKING zone ≥30 seconds. Threshold configurable per zone. | Critical |
| FR-VIO-02 | Busway lane violation | Non-authorized vehicle in BUSWAY_LANE zone at any point (static or moving). Immediate alert. | Critical |
| FR-VIO-03 | Bicycle lane violation | Motorized vehicle in BICYCLE_LANE zone ≥10 seconds. | High |
| FR-VIO-04 | Duration tracking | Real-time violation duration in dashboard, 1-second resolution. | Critical |
| FR-VIO-05 | Evidence package assembly | Compile: violation type, plate number, vehicle class, start/end timestamps, GPS coordinates, 10-second video clip, confidence score, zone ID. | Critical |
| FR-VIO-06 | Duplicate suppression | Suppress duplicate events for same Track ID in same zone during continuous violation. Single event until vehicle departs. | High |
| FR-VIO-07 | Violation state machine | States: `DETECTED → PENDING → VERIFIED → EVIDENCED → SUBMITTED → RESOLVED`. Promotion rules: `DETECTED→PENDING`: automatic on duration threshold. `PENDING→VERIFIED`: auto when YOLO conf ≥0.85 AND ANPR conf ≥0.90. Multi-camera corroboration (≥2 cameras confirm same plate) lowers VERIFIED threshold to 0.78. `DISCARDED` when YOLO <0.60. All transitions logged with actor + timestamp. No E-TLE without `VERIFIED`. | High |
| FR-VIO-08 | CRM/JAKI report classification and corroboration | CRM/JAKI sends citizen reports via OAuth 2.0 webhook (POST `/api/v1/jaki/ingest`, HMAC-SHA256 signed). JSEP classifies reports into `ILLEGAL_PARKING`, `BUSWAY_VIOLATION`, `BICYCLE_LANE_VIOLATION`, `ILLEGAL_DROPOFF`, or `OTHER`; geo-lookups nearest camera; de-duplicates against existing events; and attempts CCTV corroboration. `combined_confidence = α * citizen_score + (1-α) * cctv_score` where **α=0.6 is configurable**. ≥0.85 + CCTV confirms → auto-VERIFIED; 0.65–0.85 → PENDING; <0.65 → DISCARDED. Valid reports award 50 reputation points (stored in `citizen_points` DB table — no blockchain). | High |
| FR-VIO-09 | Ganjil-Genap violation | Stretch feature only. Detect plate parity violation on restricted corridors after core case violations are complete. Minimum ANPR confidence for Ganjil-Genap enforcement: 0.92. **Demo**: optional only, using static schedule/holiday JSON. | Medium |

### 7.5 Live Monitoring Dashboard

| Req ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-DASH-01 | Multi-camera grid view | Up to 16 live CCTV streams simultaneously with auto-highlight on active violation. | Critical |
| FR-DASH-02 | Real-time violation feed | Live events via WebSocket, <500ms latency. Show: camera, location, type, plate, thumbnail. | Critical |
| FR-DASH-03 | Interactive violation map | MapLibre GL with live violation pins. Click pin → evidence panel (video clip, ANPR result, plate history). | Critical |
| FR-DASH-04 | Spatial heatmap | H3 hex heatmap with Resolution 10 as operator default and Resolution 9 for executive overview. Toggle by: violation type, time range (15m/1h/6h/24h/7d), vehicle type, and camera readiness grade. | Critical |
| FR-DASH-05 | Statistics panel | Real-time counters: total violations today, by type, by corridor, by hour. Trend vs yesterday. | High |
| FR-DASH-06 | Officer deployment map | Current officer positions (manual input or GPS) against recommended deployment heatmap from MCLP optimizer. | High |
| FR-DASH-07 | Alert management | Alert inbox with severity sorting. Actions: confirm → E-TLE, dismiss (false positive), escalate. | Critical |
| FR-DASH-08 | Audit log viewer | Full audit trail per violation: state transitions, actor, timestamp, confidence scores. | High |
| FR-DASH-09 | Role-based access | Operations (full), Field Officer (read + acknowledge), Executive (analytics only), Admin (config). | High |
| FR-DASH-10 | Responsive layout | Functional on 10-inch tablet for field supervisors. | Medium |

### 7.6 Analytics & Intelligence

| Req ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-ANA-01 | H3 hotspot computation | KDE-based risk scores for H3 Resolution-10 operational cells and Resolution-9 executive rollups, refreshed every 15 minutes. Display top 50 hotspots. | Critical |
| FR-ANA-02 | Temporal pattern analysis | Hourly violation distribution per corridor. Peak violation windows per day-of-week. | High |
| FR-ANA-03 | Corridor ranking | Rank corridors by violation frequency, severity-weighted score, and trend direction. | High |
| FR-ANA-04 | Repeat offender tracking | Flag plates with >3 violations in 30-day window. Generate report for E-TLE unit. | Medium |
| FR-ANA-05 | Behavioural clustering | DBSCAN on violation events (type + time + location) to identify systemic vs. incidental violations. | Medium |
| FR-ANA-06 | Officer placement optimization | MCLP per shift with current demand data. Output recommended positions with coverage impact scores. | High |
| FR-ANA-07 | E-TLE camera placement | Top-10 uncovered high-risk H3 cells as new E-TLE camera installation recommendations. | Medium |

### 7.7 E-TLE Integration

| Req ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-ETLE-01 | Draft ticket generation | Auto-generate E-TLE draft from `VERIFIED` violation evidence package. Format per DISHUB E-TLE API spec (or mock spec for demo — see OQ-01). | Critical |
| FR-ETLE-02 | Human-in-the-loop approval | All tickets require one-click approval from authorized E-TLE officer. No fully autonomous ticketing in v1. | Critical |
| FR-ETLE-03 | Evidence attachment | Attach best photo frame, video clip URL, ANPR result, confidence score to each submission. | Critical |
| FR-ETLE-04 | Submission status tracking | Track E-TLE lifecycle: `DRAFT → SUBMITTED → ISSUED → PAID → CONTESTED`. Reconcile with E-TLE responses. | High |
| FR-ETLE-05 | Bulk review interface | E-TLE officer reviews/approves up to 20 violations in a single batch interface. | High |
| FR-ETLE-06 | Legal/sanction lookup | Attach deterministic legal basis, sanction/fine reference, and evidence checklist from FR-LEGAL-01 to every E-TLE draft and executive report. | Critical |

**Ticket Number Format**:  
`ETL-{YYYY}{MM}{DD}-{KODE_WLKT}-{VIO_CODE}-{SEQ:06d}-{CHECK}`  
Example: `ETL-20260526-JKP-ILP-000247-3`  
- KODE_WLKT: JKP / JKS / JKT / JKU / JKB  
- VIO_CODE: ILP (illegal parking) / BLV (busway lane) / BCV (bicycle lane) / IDO (illegal drop-off) / GGV (Ganjil-Genap stretch)  
- CHECK: Luhn mod-10 checksum  
- Also encoded as QR (ISO 18004) in E-TLE PDF  

### 7.8 Alert Dispatch Architecture

On `VERIFIED`, four parallel Kafka consumers dispatch alerts. **Bulkhead pattern** — single consumer failure does not block others. All wrapped with circuit breaker + dead-letter-queue.

| Consumer | Channel | SLA | Fallback |
|---|---|---|---|
| Officer Dispatch | Web/PWA dispatch view — P1 HIGH priority alert | <3s | SMS/WhatsApp gateway after 30s if configured |
| WebSocket | Dashboard — Socket.IO with Redis pub/sub | <500ms | Missed events replayed from Kafka offset |
| E-TLE Draft | Write to `etle_submissions` (status=DRAFT) + PDF generation | <90s | Dead-letter-queue + retry ×5, cap 60s |
| CRM Outbound | POST to DISHUB CRM (HMAC-SHA256) + JAKI callback | <5s | DLQ + exponential retry |

#### Relevant-Unit Routing Matrix

This directly supports the competition requirement that combinations of violation types are sent to the relevant unit.

| Condition | Primary Routing | Secondary Routing | Demo Action |
|---|---|---|---|
| Illegal parking in no-parking zone | Parking enforcement / field patrol | E-TLE review when camera readiness = A | Create dispatch task + E-TLE draft |
| Busway lane occupancy | Corridor enforcement / TransJakarta liaison | E-TLE review | Immediate high-priority alert |
| Bicycle lane occupancy | Road discipline field unit | CRM/JAKI callback if citizen-sourced | Alert + hotspot count |
| Public transport pick-up/drop-off outside stop | Public transport supervision unit | Field patrol | Dispatch task with vehicle class + stop name |
| Repeated same-location violations | Operations planning | E-TLE camera placement simulator | Add to camera installation candidate list |
| Multiple violation types in same H3 cell within 1h | Command center supervisor | Relevant units by type | Create combined hotspot incident |

#### FR-LEGAL-01: Deterministic Legal & Sanction Reference

This is **core v1**. JSEP must map every violation type to the legal basis, internal classification, sanction/fine reference, evidence requirements, and report wording fragments without using an LLM.

| Field | Requirement |
|---|---|
| **Req ID** | FR-LEGAL-01 |
| **Purpose** | Provide auditable rule/sanction references for E-TLE drafts, officer dispatch, CRM callbacks, and executive summaries |
| **Input** | `violation_type`, `zone_type`, `vehicle_class`, `duration_s`, `corridor`, `camera_readiness_grade` |
| **Output** | legal basis code, citation text, sanction/fine reference, required evidence checklist, relevant unit, static BA/report wording fragment |
| **Storage** | PostgreSQL tables: `legal_references`, `sanction_references`, `violation_legal_map` |
| **Authoring Format** | Versioned YAML/JSON fixtures reviewed by legal/operations team before loading to DB |
| **Runtime Rule** | No free-form generation; lookup must be deterministic and audit-logged |

Example mapping:

```yaml
ILLEGAL_PARKING:
  legal_basis_code: "UU_LLAJ_22_2009_PASAL_287"
  citation_text: "Pelanggaran terhadap rambu/marka larangan berhenti atau parkir"
  sanction_ref: "SANCTION_PARKING_DKI_DEFAULT"
  evidence_required:
    - plate_number
    - vehicle_class
    - no_parking_zone_id
    - duration_seconds
    - best_frame_url
    - video_clip_url
  relevant_unit: "parking_enforcement"
  static_report_fragment: "Kendaraan terdeteksi berhenti/parkir pada zona larangan selama {duration_seconds} detik."
```

The executive summary uses this same table to aggregate violations by legal basis and sanction category. This keeps daily reports legally grounded even when the optional LLM/RAG service is disabled.

#### FR-REP-06: Optional RAG-Assisted Berita Acara Generation (NarrativeAgent)

**Competition priority**: Low. This feature supports E-TLE drafting, but it is not a core requirement of the competition case. The demo should rely on a deterministic Jinja2/ReportLab template first; RAG is an optional assistant for legal-language drafting after the core detection, CRM, dashboard, and simulator features work.

**Why optional RAG**: A RAG pipeline can retrieve relevant Pasal/Ayat, Pergub reference, and approved wording for the specific violation type. Output remains **reviewer-assist text**, not automatically court-admissible evidence, and every generated narrative requires human approval.

| Field | Value |
|---|---|
| **Req ID** | FR-REP-06 |
| **LLM Provider** | Configurable Google Gemini API model via Google GenAI SDK, or equivalent enterprise-approved model |
| **API Key Config** | `GEMINI_API_KEY` environment variable. **Never hardcode the key.** |
| **Model Config** | `GEMINI_MODEL` environment variable selected from the current Google AI Studio/API model list |
| **Embedding Model** | `gemini-embedding-2` for knowledge base indexing |
| **Vector Store** | ChromaDB (local, no server required — `pip install chromadb`) |
| **Knowledge Base** | Legal corpus in `rag_corpus/`: `uu_llaj_22_2009_relevant.txt`, `pergub_dki_155_2018_ganjilgenap.txt`, `pm_perhubungan_15_2019_halte.txt`, `pm_kemenhub_025.txt`, `pergub_dki_88_2019.txt`, `daftar_sanksi_pelanggaran.txt`, and BA templates such as `ba_*.txt`, `berita_acara_*.txt`, `c-14.-berita-acara-serah-terima-barang.txt` |

**RAG Architecture**:

```
┌──────────────────────────────────────────────────────┐
│  KNOWLEDGE BASE (rag_corpus/)                         │
│  UU LLAJ · Pergub · PM Perhubungan · BA Templates    │
│  → Chunked (512 tokens, 50 overlap)                  │
│  → Embedded: gemini-embedding-2                      │
│  → Stored: ChromaDB collection "jsep_legal"          │
└────────────────┬─────────────────────────────────────┘
                 │ Top-5 relevant chunks (cosine sim)
                 ▼
┌──────────────────────────────────────────────────────┐
│  RETRIEVAL QUERY:                                     │
│  "{violation_type} {zone_type} {duration}s Jakarta"   │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│  PROMPT ASSEMBLY (rag_agent.py)                       │
│  System: "Kamu adalah sistem JSEP DISHUB DKI          │
│   Jakarta. Buat berita acara resmi berdasarkan        │
│   konteks hukum berikut. Gunakan bahasa formal        │
│   Indonesian. Output hanya teks BA, tidak ada         │
│   komentar tambahan."                                 │
│                                                       │
│  Context: [retrieved legal chunks]                    │
│  Violation: {plate, type, zone, duration, timestamp,  │
│              camera_id, officer_approving}            │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│  GEMINI API MODEL → Structured BA Output             │
│  max_tokens: 800 · temperature: 0.1 (deterministic)  │
└──────────────────────────────────────────────────────┘
```

**Implementation** (`narrative_agent.py`):

```python
# narrative_agent.py
import os
import google.generativeai as genai
import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]  # from .env — NEVER hardcode
genai.configure(api_key=GEMINI_API_KEY)

# Vector store setup (run once at startup)
embedding_fn = GoogleGenerativeAiEmbeddingFunction(
    api_key=GEMINI_API_KEY,
    model_name="models/gemini-embedding-2"
)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="jsep_legal",
    embedding_function=embedding_fn
)

def index_legal_corpus(corpus_dir: str = "rag_corpus/"):
    """Run once to build the vector index from legal documents."""
    from pathlib import Path
    import re
    for doc_path in Path(corpus_dir).glob("*.txt"):
        text = doc_path.read_text(encoding="utf-8")
        # Chunk: 512 chars, 50 char overlap
        chunks = [text[i:i+512] for i in range(0, len(text), 462)]
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                ids=[f"{doc_path.stem}_{i}"],
                metadatas=[{"source": doc_path.stem}]
            )
    print(f"Indexed {collection.count()} chunks.")

def generate_berita_acara(violation: dict) -> str:
    """
    Generate berita acara via RAG + Gemini.
    violation: {plate, violation_type, zone_name, duration_s,
                timestamp, camera_id, officer_id, confidence}
    Returns: berita acara text (str)
    """
    # Step 1: Retrieve relevant legal context
    query = f"{violation['violation_type']} {violation['zone_name']} {violation['duration_s']}s Jakarta"
    results = collection.query(query_texts=[query], n_results=5)
    legal_context = "\n\n---\n\n".join(results["documents"][0])

    # Step 2: Build prompt
    system_prompt = (
        "Kamu adalah sistem otomatis JSEP milik Dinas Perhubungan DKI Jakarta. "
        "Tugas kamu adalah membuat berita acara pelanggaran lalu lintas yang formal, "
        "ringkas, dan mengacu pada dasar hukum yang tepat. "
        "Output HANYA teks berita acara, tanpa komentar tambahan, tanpa markdown."
    )
    user_prompt = f"""
Konteks Hukum:
{legal_context}

Data Pelanggaran:
- Nomor Polisi    : {violation['plate']}
- Jenis Pelanggaran: {violation['violation_type']}
- Lokasi/Zona     : {violation['zone_name']}
- Durasi          : {violation['duration_s']} detik
- Waktu Kejadian  : {violation['timestamp']}
- Kamera ID       : {violation['camera_id']}
- Petugas Verifikasi: {violation['officer_id']}
- Confidence Score: {violation['confidence']:.3f}

Buat berita acara resmi sesuai format standar DISHUB DKI Jakarta.
"""
    # Step 3: Generate with Gemini
    model = genai.GenerativeModel(
        model_name=os.environ["GEMINI_MODEL"],
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=800,
            temperature=0.1  # near-deterministic for legal text
        )
    )
    try:
        response = model.generate_content([system_prompt, user_prompt])
        return response.text.strip()
    except Exception as e:
        # Fallback: Jinja2 static template — E-TLE NOT blocked
        return _static_ba_fallback(violation)

def _static_ba_fallback(v: dict) -> str:
    """Static Jinja2 fallback — no LLM required."""
    from jinja2 import Template
    template = Template(open("templates/berita_acara_static.j2").read())
    return template.render(**v)
```

**Knowledge Base Files** (`rag_corpus/`):

| File | Content | Chunk Count (est.) |
|---|---|---|
| `uu_llaj_22_2009_relevant.txt` | Pasal 287 (kecepatan/lajur), 284 (pejalan kaki), 275 (parkir), 106 (rambu) | ~40 chunks |
| `pergub_dki_155_2018_ganjilgenap.txt` | Full Ganjil-Genap regulation text + jadwal | ~15 chunks |
| `pm_perhubungan_15_2019_halte.txt` | Pasal 34 (larangan berhenti di luar halte) | ~10 chunks |
| `ba_pemeriksaan_fisik_hasil_pekerjaan.txt` | BA procurement template source from corpus | ~1 chunk |
| `ba_laporan_penyelesaian_pekerjaan.txt` | BA procurement template source from corpus | ~1 chunk |
| `ba_pengelolaanaset2021kepgub0031487.txt` | BA procurement template source from corpus | ~16 chunks |
| `ba_surat_tagihan.txt` | BA procurement template source from corpus | ~1 chunk |
| `ba_negosiasi_teknis_dan_harga.txt` | BA procurement template source from corpus | ~1 chunk |
| `berita_acara_pemberian_penjelasan.txt` | BA procurement template source from corpus | ~5 chunks |
| `berita_acara_pemberian_penjelasan_kualifikasi.txt` | BA procurement template source from corpus | ~3 chunks |
| `berita_acara_pemeriksaan_hasil_pekerjaan.txt` | BA procurement template source from corpus | ~0-1 chunk |
| `berita_acara_pengumuman_negosiasi.txt` | BA procurement template source from corpus | ~1 chunk |
| `c-14.-berita-acara-serah-terima-barang.txt` | BA procurement template source from corpus | ~1 chunk |
| `daftar_sanksi_pelanggaran.txt` | Penalty schedule: violation → pasal → denda | ~12 chunks |

**Cost Model (Gemini API — verify before demo)**:
- Input: ~1,500 tokens/call (legal context + violation data)
- Output: ~800 tokens/call
- Cost: must be re-estimated from current Google pricing during deployment week
- Demo fallback: static Jinja2 template works with zero LLM cost

| Condition | Behavior |
|---|---|
| Gemini API available | Full RAG generation |
| API timeout (>10s) | 3× exponential retry (1s, 2s, 4s) → static Jinja2 fallback |
| Rate limit (429) | Queue with 30s delay → static fallback if queue >5 min |
| ChromaDB unavailable | Skip retrieval → Gemini with violation data only (no legal context) |
| Any LLM failure | Static Jinja2 → E-TLE workflow **never blocked** |

**Priority**: Low / Stretch.

### 7.9 LLM Configuration (Optional Assistive Layer)

Gemini API access is useful, especially if the team already has a valid API key. It should be integrated as an optional assistive layer, not as an enforcement dependency.

| Config | Default | Purpose |
|---|---|---|
| `ENABLE_LLM_DRAFTING` | `false` | Enables optional reviewer-assist text drafting only |
| `GEMINI_API_KEY` | unset | Runtime secret for Gemini API; never committed |
| `GEMINI_MODEL` | unset | Configurable model selected from current Google AI Studio/API model list |

Allowed uses:
- Improve wording of executive summaries after deterministic metrics are computed.
- Draft reviewer-assist berita acara text using FR-LEGAL-01 references as grounding.
- Summarize daily trends for stakeholder reports.
- Generate read-only "AI Insight" text from deterministic violation clusters.

Disallowed uses:
- Deciding whether a violation occurred.
- Determining legal basis, sanction/fine, or E-TLE eligibility.
- Submitting or approving enforcement actions.

#### FR-INSIGHT-01: Optional AI Insight Agent

This is an **optional v1 demo enhancement**, not a required enforcement component. It is the best-practice version of the proposed "swarm narrative agent": JSEP does not need a separate swarm framework because Kafka consumers already behave like autonomous processing services. What can add demo value is a read-only LLM summarizer that turns deterministic analytics into actionable Indonesian brief text.

| Field | Requirement |
|---|---|
| **Req ID** | FR-INSIGHT-01 |
| **Purpose** | Produce concise executive/operations insight from already-computed violation clusters |
| **Input** | `cluster_id`, violation counts, time window, location/corridor, top violation types, active cameras, camera readiness, recommended unit, officer/camera placement recommendation |
| **Output** | Strict JSON: `priority`, `summary`, `recommended_action`, `reasoning`, `confidence_note`, `source_cluster_id` |
| **Provider** | Configurable Gemini model via `GEMINI_MODEL` when `ENABLE_AI_INSIGHTS=true` |
| **Runtime Rule** | Read-only; cannot create, verify, submit, approve, or dismiss violations |
| **Fallback** | Hide AI Insight panel or show deterministic template summary if Gemini fails |

Guardrails:
- The prompt must state that the model may only summarize supplied JSON and must not invent plates, cameras, laws, sanctions, or locations.
- Output must pass JSON schema validation before rendering.
- Every insight must link back to source cluster/event IDs so operators can inspect the underlying evidence.
- Insights are never sent directly to E-TLE or field officers without the deterministic dispatch record.

Example output:

```json
{
  "priority": "HIGH",
  "summary": "Pelanggaran parkir liar meningkat di koridor Sudirman dalam 20 menit terakhir.",
  "recommended_action": "Prioritaskan patroli parkir pada dua titik hotspot dengan kamera readiness A/B.",
  "reasoning": "Cluster berisi 9 pelanggaran, 6 masih aktif, dan terjadi pada jam puncak pagi.",
  "confidence_note": "Berdasarkan cluster CLU-20260531-0007 dan bukan keputusan penindakan otomatis.",
  "source_cluster_id": "CLU-20260531-0007"
}
```

### 7.10 Government API Integration (MOCK for Demo)

> **⚠️ CRITICAL FOR AI AGENT**: The following government APIs **CANNOT** be accessed in a competition prototype. They require formal MoU with government agencies (6–18 months minimum). For all demo purposes, these are **MOCK/STUB** implementations. All code must use `USE_MOCK_APIS=true` flag in `.env`.

| API | Real Endpoint | Demo Implementation | Data Needed for Ticket |
|---|---|---|---|
| Korlantas Polri (vehicle lookup) | `korlantas.polri.go.id/api-etle` (mTLS) | `MockKorlantasClient` — returns seeded owner data from fixture JSON | owner_name, vehicle_brand, model, color |
| SAMSAT Online (tax status) | National SAMSAT API | `MockSamsatClient` — returns `LUNAS` for all plates in demo | pajak_status, STNK_status |
| Ditjen Dukcapil (identity) | Kemendagri API (MoU Perpres 39/2019) | **NOT IMPLEMENTED** — feature moved to Future Roadmap | N/A in v1 |

```python
# config.py
USE_MOCK_APIS = os.getenv("USE_MOCK_APIS", "true").lower() == "true"

# government_apis.py
def get_vehicle_owner(plate: str) -> VehicleOwner:
    if USE_MOCK_APIS:
        return MockKorlantasClient.lookup(plate)  # returns fixture data
    else:
        return KorlantasClient.lookup(plate)  # requires mTLS cert — production only
```

Mock fixtures in `fixtures/vehicle_registry_mock.json` — populated with synthetic Jakarta plate data for 500+ demo vehicles.

---

## 8. Non-Functional Requirements

| Req ID | Requirement | Target | Notes |
|---|---|---|---|
| NFR-01 | End-to-end latency | <3s (edge), <5s (cloud-only demo) | From violation start to dashboard alert |
| NFR-02 | Dashboard uptime | >99.5% during 06:00–24:00 | |
| NFR-03 | Concurrent streams | ≥50 per processing node | |
| NFR-04 | API response time | P95 <200ms for read endpoints | Excluding /optimizer/placement (compute endpoint) |
| NFR-05 | Data retention | Raw frames: 24h (non-violation-linked). Violation records: per E-TLE statutory period. Evidence clips: 90 days. | UU PDP compliance |
| NFR-06 | Security | TLS 1.3 for all endpoints. OAuth 2.0 for API auth. AES-256-GCM for PII at rest. Append-only audit log. | |
| NFR-07 | Evidence integrity | SHA-256 hash on all video evidence clips. Hash stored in `evidence_packages.sha256_hash`. | Legal chain of custody |
| NFR-08 | YOLO26 license | AGPL-3.0 for prototype. Ultralytics Enterprise License required for production government deployment. | Evaluate before production |

---

## 9. Technology Stack

### 9.1 AI / ML

| Component | Technology | Notes |
|---|---|---|
| Detection model | YOLO26 (Ultralytics) — fallback: YOLOv11 | AGPL-3.0 |
| Tracking | BoxMOT v10+ (BoT-SORT + OSNet ReID) | MIT-ish license |
| OCR | PaddleOCR 3.5+ / PP-OCRv5, fallback PP-OCRv4 | Apache 2.0 |
| Super-resolution | Real-ESRGAN | BSD-3 |
| Rain detection | ResNet-18 (torchvision pretrained) | BSD |
| Preprocessing | OpenCV 4.x | Apache 2.0 |
| ML framework | PyTorch 2.x | BSD |

### 9.2 Backend & Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI + Uvicorn | REST + WebSocket backend |
| Message Broker | Apache Kafka 3.x | Event bus, 7-day retention |
| State Cache | Redis 7.x | Track state, WebSocket pub/sub |
| Primary DB | PostgreSQL 16 + TimescaleDB | Violations, time-series |
| Spatial DB | PostGIS 3.x | H3 hexagons, zone polygons |
| Object Storage | MinIO (S3-compatible) | Evidence clips, model artifacts |
| Spatial Index | Uber H3 v4 (h3-py) | Hotspot mapping |
| LP Solver | PuLP + GLPK | MCLP officer optimizer |
| Containers | Docker image packaging; runtime via local Docker Engine, remote VM, Kubernetes, Cloud Run, or equivalent | Docker Desktop not required; Docker Build Cloud may be used for image builds |
| Monitoring | Prometheus + Grafana + ELK | Metrics, logs, alerting |
| CI/CD | GitHub Actions + ArgoCD | Automated testing, deployment |

### 9.3 Frontend

| Component | Technology | Purpose |
|---|---|---|
| UI Framework | React 18 + TypeScript | Dashboard SPA |
| Map Library | MapLibre GL JS 4.x | Violation maps, H3 heatmap |
| Charts | Apache ECharts 5.x | Temporal charts, KPI sparklines |
| Real-time | WebSocket (native) | Live violation event stream |
| State | Zustand | Dashboard state management |
| UI Components | shadcn/ui + Tailwind CSS | Design system |
| PDF Generation | ReportLab (Python, server-side) | Executive summary PDF |

---

## 10. API Specifications

### 10.1 Violations API

| Endpoint | Method | Description | Auth |
|---|---|---|---|
| `/api/v1/violations` | GET | List violations. Filters: `date_range`, `type`, `zone`, `camera_id`, `plate`, `confidence_min`, `status` | JWT |
| `/api/v1/violations/{id}` | GET | Full violation detail: evidence package, state history, ANPR result | JWT |
| `/api/v1/violations/{id}/confirm` | POST | Officer verifies `PENDING` event → `VERIFIED`, triggers evidence packaging and E-TLE draft | JWT (role: OPERATIONS) |
| `/api/v1/violations/{id}/dismiss` | POST | Officer dismisses → `DISMISSED`, increments false positive counter | JWT (role: OPERATIONS) |
| `/api/v1/violations/live` | WS | Real-time violation event stream. Subscribe/unsubscribe per camera/zone | JWT (WS handshake) |

### 10.2 Analytics API

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/hotspots/h3` | GET | H3 cells with risk scores. Params: `resolution` (7–11), `time_window`, `violation_type` |
| `/api/v1/analytics/corridor-ranking` | GET | Corridors ranked by severity score. Params: `date_range`, `violation_type` |
| `/api/v1/analytics/temporal-pattern` | GET | 24×7 hourly violation matrix for a corridor/zone |
| `/api/v1/optimizer/placement` | GET | Run MCLP. Params: `n_officers`, `shift`, `date` |
| `/api/v1/analytics/repeat-offenders` | GET | Plates above violation threshold. Params: `min_violations`, `days_window` |

### 10.3 WebSocket Event Schema

```json
{
  "event_type": "VIOLATION_DETECTED",
  "violation_id": "uuid-v4",
  "timestamp": "2026-05-20T07:23:41.123Z",
  "camera_id": "CAM-JKT-SUDIRMAN-04",
  "location": { "lat": -6.2088, "lng": 106.8456 },
  "violation_type": "ILLEGAL_PARKING",
  "vehicle_class": "car",
  "plate_number": "B 1234 XYZ",
  "plate_confidence": 0.91,
  "plate_type": "STANDARD_PRIVATE",
  "duration_seconds": 47,
  "thumbnail_url": "https://jsep.dishub.go.id/evidence/uuid-v4/thumb.jpg",
  "status": "DETECTED",
  "composite_confidence": 0.88
}
```

### 10.4 JAKI Ingest Webhook

```
POST /api/v1/jaki/ingest
Authorization: Bearer <oauth2_token>
X-JAKI-Signature: HMAC-SHA256(<body>)

{
  "jaki_report_id": "string",
  "category": "PARKIR_LIAR" | "BUSWAY" | "SEPEDA" | "TURUN_NAIK_PENUMPANG" | "LAINNYA",
  "lat": float,
  "lng": float,
  "photo_url": "string (signed S3 URL)",
  "description": "string",
  "timestamp": "ISO8601",
  "user_id_hashed": "string (SHA-256, not reversible)"
}
```

---

## 11. Data Requirements & Training Pipeline

### 11.1 Dataset Sources (All Open/Public for Demo)

| Dataset | Volume | Source | License | Status |
|---|---|---|---|---|
| Indonesian License Plates (Roboflow merge) | ~10,000 images | Roboflow Universe: `indonesia-lpr` (Praproject, 5,582), `indonesia-license-plate-detection` (Rendika, 2,819), `indonesia-license-plate-iqrtj` (KSP Workspace, 1,652) | CC-BY 4.0 (check per dataset) | ✅ Publicly available |
| Jakarta CCTV Footage (Balitower HLS) | Up to 50K frames (scraped at 1 FPS) | `cctv.balitower.co.id` — ~6,000+ Jakarta cameras, public HLS streams | **⚠️ Verify ToS before scraping — use only for research/competition prototype; seek written clearance for production** | ⚠️ ToS review needed |
| COCO 2017 (base pretraining) | 118K images | cocodataset.org | CC-BY 4.0 | ✅ |
| OpenImages v7 (vehicle subset) | ~50K vehicle images | storage.googleapis.com/openimages | CC-BY 4.0 | ✅ |
| Jakarta Road Zone GeoJSON | Zone polygons | DISHUB GIS (request) or manually digitized from public maps | N/A | 🟡 Request or DIY |
| Holiday Calendar JSON | ~20 public holiday dates/year | Static JSON from Kemenaker published list | Public domain | ✅ |
| Weather timestamps (BMKG) | Historical rain events | api.bmkg.go.id | Public domain | ✅ |

> **⚠️ Balitower Note**: "Publicly accessible without authentication" does NOT equal "legally scrape-able." For competition prototype: scrape limited frames, clearly label as competition research, do not redistribute raw footage. For production: seek explicit written permission from Balitower.

### 11.2 Annotation Pipeline (OpenCV + CVAT)

```
Data Collection:
  ├── Roboflow API → download pre-annotated plate datasets (auto)
  ├── Balitower HLS scraper → raw frames at 1 FPS (manual annotation needed)
  └── DISHUB sample footage (if provided)

Annotation Tool:
  └── CVAT (Computer Vision Annotation Tool) — self-hosted, free
      └── Semi-automated: YOLO26 pretrained predictions → human review/correction
          (Active Learning loop: model predicts → human reviews → corrected labels fed back)

Label Format: YOLO format (.txt) with 8 classes:
  0: car
  1: motorcycle
  2: truck
  3: bus
  4: angkot
  5: bajaj
  6: bicycle
  7: pedestrian
  + Separate plate dataset: 1 class (license_plate)

Annotation target (MVP):
  - Vehicle detection: 10,000 frames (2,500 daytime/2,500 night/2,500 rain/2,500 adverse)
  - Plate detection: 5,000 cropped plate images (all types)
  
Annotation cost estimate (if outsourced):
  - ~10K frames × 15 min/frame = 2,500 person-hours
  - At $3/hr (Indonesian freelancer rate): ~$7,500
  - Alternative: CVAT active learning reduces manual effort by ~50% → ~$3,750
```

### 11.3 OpenCV Augmentation Pipeline

```python
# augmentation.py — OpenCV-based training augmentation

import cv2
import numpy as np
from pathlib import Path

class JSEPAugmentor:
    """
    OpenCV-based augmentation for Jakarta CCTV training data.
    All operations are GPU-free (CPU OpenCV).
    """

    @staticmethod
    def add_rain_streaks(img: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """Simulate rain using directional line overlay."""
        rain_layer = np.zeros_like(img)
        num_drops = int(500 * intensity)
        for _ in range(num_drops):
            x = np.random.randint(0, img.shape[1])
            y = np.random.randint(0, img.shape[0])
            length = np.random.randint(5, 20)
            cv2.line(rain_layer, (x, y), (x - 2, y + length), (200, 200, 200), 1)
        return cv2.addWeighted(img, 1.0, rain_layer, 0.4 * intensity, 0)

    @staticmethod
    def simulate_night(img: np.ndarray, gamma: float = 0.3) -> np.ndarray:
        """Simulate night lighting with gamma adjustment."""
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype=np.uint8)
        return cv2.LUT(img, table)

    @staticmethod
    def apply_clahe(img: np.ndarray) -> np.ndarray:
        """CLAHE for low-light normalization (also used in inference pipeline)."""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    @staticmethod
    def add_motion_blur(img: np.ndarray, kernel_size: int = 9) -> np.ndarray:
        """Simulate vehicle motion blur."""
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size) / kernel_size
        return cv2.filter2D(img, -1, kernel)

    @staticmethod
    def add_jpeg_artifacts(img: np.ndarray, quality: int = 50) -> np.ndarray:
        """Simulate CCTV stream compression artifacts."""
        _, encoded = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    def augment(self, img: np.ndarray, mode: str = 'random') -> np.ndarray:
        """Apply random combination of augmentations."""
        augmentations = [
            lambda x: self.add_rain_streaks(x, intensity=np.random.uniform(0.2, 0.8)),
            lambda x: self.simulate_night(x, gamma=np.random.uniform(0.1, 0.4)),
            lambda x: self.apply_clahe(x),
            lambda x: self.add_motion_blur(x, kernel_size=np.random.choice([3, 5, 7, 9])),
            lambda x: self.add_jpeg_artifacts(x, quality=np.random.randint(40, 70)),
        ]
        if mode == 'random':
            selected = np.random.choice(augmentations, size=np.random.randint(1, 3), replace=False)
            for aug in selected:
                img = aug(img)
        return img
```

### 11.4 Training Script (YOLO26 Fine-Tuning)

```python
# train_jsep.py

from ultralytics import YOLO
import os

def train_vehicle_detector():
    model = YOLO("yolo26n.pt")  # or "yolo11n.pt" as fallback
    
    results = model.train(
        data="datasets/jsep_vehicles/dataset.yaml",
        epochs=100,
        imgsz=640,
        batch=16,               # Single RTX 4090 (realistic demo hardware)
        device="0",             # GPU index
        optimizer="SGD",        # MuSGD if YOLO26 supports; SGD as fallback
        patience=20,            # Early stopping
        project="runs/jsep",
        name="vehicle_detector_v1",
        exist_ok=True,
        # Augmentation (YOLO native + custom via albumentations)
        mosaic=1.0,
        flipud=0.0,             # No vertical flip for traffic cameras
        fliplr=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,           # Slight rotation for angled cameras
        translate=0.1,
        scale=0.5,
    )
    return results

def train_plate_detector():
    model = YOLO("yolo26s.pt")  # or "yolo11s.pt" as fallback
    
    results = model.train(
        data="datasets/jsep_plates/dataset.yaml",
        epochs=150,
        imgsz=640,
        batch=16,
        device="0",
        patience=25,
        project="runs/jsep",
        name="plate_detector_v1",
        exist_ok=True,
    )
    return results

if __name__ == "__main__":
    print("Training vehicle detector...")
    train_vehicle_detector()
    print("Training plate detector...")
    train_plate_detector()
    print("Training complete. Evaluate with: yolo val model=runs/jsep/vehicle_detector_v1/weights/best.pt data=...")
```

---

## 12. Database Schema

### 12.1 Core Tables

```sql
-- violations: main fact table (TimescaleDB time-partitioned)
CREATE TABLE violations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id       VARCHAR(64) REFERENCES cameras(id),
    track_id        VARCHAR(64) NOT NULL,
    violation_type  VARCHAR(32) NOT NULL CHECK (violation_type IN (
                        'ILLEGAL_PARKING','BUSWAY_VIOLATION','BICYCLE_LANE_VIOLATION',
                        'ILLEGAL_DROPOFF','GANJIL_GENAP')),
    zone_id         UUID REFERENCES zones(id),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,
    duration_seconds INTEGER,
    status          VARCHAR(32) DEFAULT 'DETECTED',
    composite_confidence DECIMAL(4,3),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
SELECT create_hypertable('violations', 'start_time');

-- anpr_results
CREATE TABLE anpr_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    violation_id    UUID REFERENCES violations(id),
    plate_raw       VARCHAR(32),
    plate_cleaned   VARCHAR(32),
    plate_type      VARCHAR(32),  -- STANDARD_PRIVATE, GOVERNMENT, MILITARY, DIPLOMATIC, ELECTRIC
    plate_color     VARCHAR(16),  -- white, yellow, red, blue, black
    confidence      DECIMAL(4,3),
    ocr_engine      VARCHAR(32) DEFAULT 'paddleocr_v4',
    frame_url       TEXT,
    quality_score   DECIMAL(4,3),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- evidence_packages
CREATE TABLE evidence_packages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    violation_id    UUID REFERENCES violations(id) UNIQUE,
    video_clip_url  TEXT,
    best_frame_url  TEXT,
    sha256_hash     VARCHAR(64) NOT NULL,
    storage_tier    VARCHAR(16) DEFAULT 'hot',  -- hot / warm / cold
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- cameras (PostGIS)
CREATE TABLE cameras (
    id              VARCHAR(64) PRIMARY KEY,
    location        GEOMETRY(POINT, 4326),
    fov_polygon     GEOMETRY(POLYGON, 4326),
    zone_ids        UUID[],
    stream_url      TEXT,
    stream_type     VARCHAR(8) DEFAULT 'rtsp',
    status          VARCHAR(16) DEFAULT 'online',
    last_heartbeat  TIMESTAMPTZ,
    source          VARCHAR(32),  -- 'dishub', 'balitower', 'atcs'
    readiness_grade VARCHAR(1) DEFAULT 'B' CHECK (readiness_grade IN ('A','B','C')),
    readiness_score DECIMAL(4,3),
    readiness_reason JSONB
);

-- zones (PostGIS)
CREATE TABLE zones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_type       VARCHAR(32) NOT NULL,
    geometry        GEOMETRY(POLYGON, 4326),
    threshold_s     INTEGER DEFAULT 30,   -- violation duration threshold
    active_hours    JSONB,  -- {"start": "00:00", "end": "23:59", "days": [1,2,3,4,5,6,7]}
    name            VARCHAR(128),
    corridor        VARCHAR(64)
);

-- h3_hotspots (TimescaleDB 15-min snapshots)
CREATE TABLE h3_hotspots (
    h3_index        VARCHAR(16) NOT NULL,
    resolution      INTEGER DEFAULT 9,
    risk_score      DECIMAL(5,4),
    violation_count_7d INTEGER,
    top_violation_type VARCHAR(32),
    computed_at     TIMESTAMPTZ NOT NULL
);
SELECT create_hypertable('h3_hotspots', 'computed_at');

-- etle_submissions
CREATE TABLE etle_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    violation_id    UUID REFERENCES violations(id),
    ticket_number   VARCHAR(48) UNIQUE,
    status          VARCHAR(16) DEFAULT 'DRAFT',
    draft_created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_by     VARCHAR(64),  -- officer user_id
    submitted_at    TIMESTAMPTZ,
    berita_acara_url TEXT,
    is_mock         BOOLEAN DEFAULT TRUE  -- flag for demo submissions
);

-- legal_references: deterministic legal basis catalog, not LLM-generated
CREATE TABLE legal_references (
    code            VARCHAR(64) PRIMARY KEY,
    title           VARCHAR(256) NOT NULL,
    citation_text   TEXT NOT NULL,
    source_doc      VARCHAR(128),
    source_article  VARCHAR(64),
    effective_from  DATE,
    effective_to    DATE,
    version         VARCHAR(32) DEFAULT 'demo_v1',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- sanction_references: deterministic sanction/fine catalog
CREATE TABLE sanction_references (
    code            VARCHAR(64) PRIMARY KEY,
    title           VARCHAR(256) NOT NULL,
    fine_min_idr    INTEGER,
    fine_max_idr    INTEGER,
    action_type     VARCHAR(64), -- warning / ticket / tow / officer_dispatch / other
    notes           TEXT,
    version         VARCHAR(32) DEFAULT 'demo_v1',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- violation_legal_map: maps each violation type to legal basis and sanction reference
CREATE TABLE violation_legal_map (
    violation_type  VARCHAR(32) PRIMARY KEY CHECK (violation_type IN (
                        'ILLEGAL_PARKING','BUSWAY_VIOLATION','BICYCLE_LANE_VIOLATION',
                        'ILLEGAL_DROPOFF','GANJIL_GENAP')),
    legal_code      VARCHAR(64) REFERENCES legal_references(code),
    sanction_code   VARCHAR(64) REFERENCES sanction_references(code),
    relevant_unit   VARCHAR(64),
    evidence_required JSONB NOT NULL,
    static_report_fragment TEXT,
    version         VARCHAR(32) DEFAULT 'demo_v1',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- crm_reports: citizen/public complaint integration and classification
CREATE TABLE crm_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_report_id  VARCHAR(128) UNIQUE,
    source              VARCHAR(32) NOT NULL,  -- JAKI / CRM / manual
    category_raw        VARCHAR(64),
    category_normalized VARCHAR(32) CHECK (category_normalized IN (
                            'ILLEGAL_PARKING','BUSWAY_VIOLATION',
                            'BICYCLE_LANE_VIOLATION','ILLEGAL_DROPOFF','OTHER')),
    report_location     GEOMETRY(POINT, 4326),
    photo_url           TEXT,
    description         TEXT,
    user_id_hashed      VARCHAR(64),
    citizen_score       DECIMAL(4,3),
    cctv_score          DECIMAL(4,3),
    combined_confidence DECIMAL(4,3),
    linked_violation_id UUID REFERENCES violations(id),
    status              VARCHAR(32) DEFAULT 'PENDING',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- unit_dispatches: routes violation combinations to relevant units
CREATE TABLE unit_dispatches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    violation_id    UUID REFERENCES violations(id),
    crm_report_id   UUID REFERENCES crm_reports(id),
    target_unit     VARCHAR(64) NOT NULL,
    dispatch_reason VARCHAR(128),
    priority        VARCHAR(16) DEFAULT 'NORMAL',
    status          VARCHAR(32) DEFAULT 'QUEUED',
    assigned_at     TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- citizen_points (replaces blockchain SBT)
CREATE TABLE citizen_points (
    user_id_hashed  VARCHAR(64) PRIMARY KEY,
    points          INTEGER DEFAULT 0,
    verified_reports INTEGER DEFAULT 0,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

-- audit_log (append-only)
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64),
    action_type     VARCHAR(64) NOT NULL,
    resource_type   VARCHAR(32),
    resource_id     UUID,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    ip_address      INET,
    outcome         VARCHAR(16),
    metadata        JSONB
);
-- Enforce append-only:
CREATE RULE no_update_audit AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE RULE no_delete_audit AS ON DELETE TO audit_log DO INSTEAD NOTHING;
```

---

## 13. Risk Register

| Risk ID | Risk | Severity | Mitigation |
|---|---|---|---|
| RISK-01 | Low CCTV quality makes ANPR unreliable | HIGH | Human review queue for confidence <0.75. Never auto-submit low-confidence to E-TLE. Report quality metrics to DISHUB. |
| RISK-02 | Insufficient Jakarta training data | HIGH | Supplement with synthetic augmentation (rain/night/compression). Active learning: reviewed frames auto-added monthly. Use public Roboflow datasets as base. |
| RISK-03 | Legal challenge to AI-generated evidence | HIGH | Mandatory human-in-the-loop approval for all E-TLE. Full audit trail. Confidence scores visible in every submission. Legal review with Biro Hukum before production. |
| RISK-04 | Edge node network latency | MEDIUM | Process detection at edge (Jetson). Send structured JSON events (not raw video) to central via Kafka. Offline queue: RocksDB WAL on Jetson SSD (72h retention). |
| RISK-05 | Privacy compliance (UU PDP) | MEDIUM | Raw CCTV frames deleted after 24h (non-violation-linked). PII (plate, NIK if applicable) AES-256-GCM encrypted at rest. Data lineage documented. |
| RISK-06 | High false positive rate erodes trust | HIGH | Conservative confidence thresholds. False positive rate as core KPI (target <8%). Easy one-click dismiss with feedback capture. Monthly threshold calibration. |
| RISK-07 | YOLO26 AGPL-3.0 licensing for government use | MEDIUM | Evaluate Ultralytics Enterprise License before production deployment. YOLOv11 (same license) as fallback — no change in risk. |
| RISK-08 | Edge hardware procurement delay | MEDIUM | System operates in cloud-only mode with 5s latency (vs 3s edge target). Deploy edge nodes at highest-violation corridors first. |
| RISK-09 | Balitower CCTV scraping — ToS/legal risk | MEDIUM | Limit scraping to competition prototype only. Seek explicit written clearance from Balitower for training data. Do not redistribute raw footage. |
| RISK-10 | Government APIs unavailable in demo | HIGH (KNOWN) | **Mitigated by design**: all government APIs are MOCK/STUB in demo. Flag `USE_MOCK_APIS=true` in all demo environments. |
| RISK-11 | PRD/demo drifts toward non-case features | MEDIUM | Competition guardrails: core pitch must show four case violations, ANPR/duration, hotspot dashboard, CRM automation, and officer/E-TLE camera simulator before stretch features. |

---

## 14. Implementation Roadmap

> **Resource assumption**: 3–4 person team. 1 GPU workstation (RTX 4090 or cloud equivalent). No A100 cluster — training adapted accordingly (see Section 16).

### Phase 1 — Foundation (Weeks 1–3)

- [ ] Runtime stack selected: local Docker Compose, managed cloud services, or remote VM. Docker Build Cloud may be used for image builds, not service runtime.
- [ ] CCTV stream ingestion service (FFmpeg + GStreamer wrapper)
- [ ] YOLO26n baseline (pretrained COCO) — no fine-tuning yet
- [ ] BoxMOT BoT-SORT integration + zone intersection logic
- [ ] Core violation rule engine (4 violation types)
- [ ] FastAPI backend: core violation CRUD endpoints

### Phase 2 — AI Model Development (Weeks 2–5)

- [ ] Download and merge Roboflow Indonesian plate datasets
- [ ] Build OpenCV augmentation pipeline (Section 11.3)
- [ ] Annotate 5,000 Jakarta CCTV frames via CVAT (active learning)
- [ ] Fine-tune YOLO26n on Jakarta vehicle dataset (10K frames MVP)
- [ ] Fine-tune YOLO26s on plate detection dataset
- [ ] Build full ANPR pipeline: PaddleOCR 3.5+ / PP-OCRv5 + regex + confidence scoring
- [ ] Real-ESRGAN super-resolution integration
- [ ] Evaluate against KPI-01 through KPI-05 on held-out test set

### Phase 3 — Analytics & Dashboard (Weeks 4–7)

- [ ] H3 hotspot computation pipeline (15-minute refresh, Resolution 10 operator default + Resolution 9 executive rollup)
- [ ] MCLP officer placement optimizer (PuLP + GLPK)
- [ ] React dashboard: live map, violation feed, H3 heatmap, alert management
- [ ] WebSocket real-time event streaming
- [ ] E-TLE draft generation + human-review approval workflow
- [ ] Role-based access control (4 roles)

### Phase 4 — Integration & Hardening (Weeks 6–9)

- [ ] JAKI/CRM webhook integration (citizen report pipeline)
- [ ] Mock government API clients (KorlantasClient, SamsatClient)
- [ ] Legal/sanction reference fixtures and deterministic lookup service (FR-LEGAL-01)
- [ ] ReportLab executive PDF generation
- [ ] Optional NarrativeAgent with Jinja2 static fallback (FR-REP-06)
- [ ] Audit log (append-only PostgreSQL rules)
- [ ] Security: TLS, OAuth 2.0, PII encryption
- [ ] Load test: 50 concurrent streams, API P95 <200ms

### Phase 5 — Trial & Demo Prep (Weeks 8–12)

- [ ] Pilot: 10 demo camera feeds across protocol roads and public-facility areas (stations/markets)
- [ ] Calibrate ANPR confidence thresholds on real Jakarta footage
- [ ] Tune violation detection thresholds per zone type
- [ ] Model retraining with trial-phase captures
- [ ] Demo scenario scripting (5 pre-defined violation scenarios for live demo)
- [ ] Executive summary trial report for DISHUB
- [ ] Documentation: API docs, operator manual, model card, data lineage

---

## 15. Demo Scope (Competition Boundary)

> **This section defines exactly what is demoed on competition day. AI Agent must not implement features outside this boundary as core demo features.**

### 15.1 In Scope for Demo

| Feature | Implementation | Data Source |
|---|---|---|
| Real-time violation detection | YOLO26 fine-tuned, live or recorded CCTV | Real Jakarta CCTV (Balitower HLS) or demo video clips |
| ANPR — Indonesian standard plates | PaddleOCR 3.5+ / PP-OCRv5 fine-tuned | Real plates from Roboflow datasets |
| Violation types (case-aligned) | Illegal parking, busway lane, bicycle lane, public transport illegal pick-up/drop-off | Rule engine on live/recorded stream |
| Live dashboard | React + MapLibre + WebSocket | Real-time from demo camera feeds |
| H3 heatmap (Resolution 10 operator + Resolution 9 executive) | TimescaleDB + h3-py | Historical seeded data + live violations |
| Officer placement optimizer | MCLP via PuLP | Seeded demand data for Jakarta corridors |
| E-TLE draft ticket | Human-in-the-loop approval UI | Mock submission (no real E-TLE API) |
| Legal/sanction reference | Deterministic lookup for rule citation, sanction/fine reference, evidence checklist | Versioned YAML/JSON fixture reviewed for demo |
| Executive summary PDF | ReportLab auto-generated with legal/sanction aggregation | Demo data from trial phase |
| CRM/JAKI citizen report flow | Report classifier + CCTV corroboration + relevant-unit routing | Demo report with sample photo |
| Ganjil-Genap detection | Optional stretch only after core demo | Simulated plates on restricted corridors |

### 15.2 Out of Scope for Demo (Future Roadmap — see Section 17)

| Feature | Reason |
|---|---|
| Live Korlantas/SAMSAT/Dukcapil API | MoU required (6–18 months) — MOCK only |
| Driver face detection + KTP match | Legal risk (UU PDP + Perpres 39/2019 scope) |
| Electronic Road Pricing (ERP) | Separate product requiring Pergub + Bapenda DKI |
| Blockchain/SBT for citizen points | Over-engineering — DB counter sufficient |
| JAKI Polygon SBT | Over-engineering — removed |
| Cross-camera ReID (full topology graph) | Requires field survey of 200+ cameras — out of scope |
| Production Kafka cluster (3-node) | Single-node Kafka sufficient for demo |

### 15.3 Demo Day Script (5 Scenarios)

1. **Scenario A — Illegal Parking**: Pre-recorded clip of car stopping in no-parking zone on Sudirman. Show: detection, ANPR read, 30-second timer, auto-alert on dashboard, evidence package, one-click E-TLE draft approval.

2. **Scenario B — Dedicated Lane Violation**: Motorcycle enters busway or bicycle lane. Show: immediate/threshold alert, confidence score, heatmap update, relevant-unit routing.

3. **Scenario C — Illegal Public Transport Pick-up/Drop-off**: Angkot/bus stops outside designated stop. Show: vehicle class, stop-zone logic, duration, dispatch to public transport supervision unit.

4. **Scenario D — Hotspot Analytics**: Switch to analytics view. Show: H3 heatmap with pre-seeded historical violations, top 10 corridors, temporal pattern (morning peak), MCLP optimizer output for 5-officer shift.

5. **Scenario E — Citizen/CRM Report**: Submit mock JAKI/CRM report with photo. Show: report classification, nearest-camera corroboration, de-duplication, combined confidence score, status callback, relevant-unit dispatch, reputation points credited.

**Optional Bonus**: Ganjil-Genap parity detection may be shown only after the five case-required scenarios above.

---

## 16. Demo Resource Plan

| Resource | Competition Prototype | Production Scale |
|---|---|---|
| Training hardware | 1× RTX 4090 (cloud, ~$2/hr) or local workstation | 4× A100 80GB |
| Training cost estimate | ~40–60 GPU hours × $2/hr = **~$100–120** | ~$50K/month |
| Annotation cost | 10K frames active learning via CVAT = ~2–3 FTE weeks **or** ~$3,500–7,500 outsourced | 50K frames: ~$20K |
| Demo CCTV feeds | 5–10 pre-recorded clips or live Balitower HLS | 200+ live cameras |
| Server | 1× cloud GPU instance (T4 or A10) for inference + 1× CPU instance for DB | Full multi-node cluster |
| Monthly cloud estimate (demo period) | ~$500–800/month (inference + storage + DB) | Production TBD |
| Team | 3–4 engineers (1 ML, 1 backend, 1 frontend, 0.5 DevOps) | Enterprise team |

> **No A100 cluster is required for competition prototype.** Training on 10K frames with a single RTX 4090 takes approximately 8–12 hours per model. The v4 PRD's claim of "4× NVIDIA A100 80GB" is production-scale infrastructure not needed for demo.

---

## 17. Future Roadmap (Out of Scope v1)

> These features are **explicitly excluded from the competition prototype**. Mention during presentation as "Phase 2 / Future Roadmap" to show vision without over-promising.

### Electronic Road Pricing (ERP) — PAD Revenue Module

Dynamic congestion pricing (Sudirman, Thamrin, Gatot Subroto). Requires:
- Separate Pergub DKI (Governor Regulation)
- Bapenda DKI integration for PAD revenue recognition  
- JakLingko MLFF API integration
- Minimum 12-month MoU process

### Driver Face Detection + Dukcapil KTP Match (FR-VIO-10)

Facial recognition on public CCTV + cosine similarity against KTP database:
- Requires MoU with Ditjen Dukcapil (Perpres 39/2019 does NOT grant third-party access)
- Privacy review under UU PDP No. 27/2022
- Technical challenge: CCTV-to-KTP photo match accuracy is low (angle, lighting, age gap)
- Defer to Phase 3 with proper legal clearance

### Live Government API Integration

- Korlantas Polri API (vehicle owner lookup)  
- SAMSAT Online (tax status)
- Ditjen Dukcapil API (identity)

All require formal MoU. Estimated timeline: 6–18 months. Replace MOCK clients with real clients post-MoU.

### Cross-Camera Full Topology Graph

Automated camera topology discovery requires FOV calibration and overlap mapping across 200+ cameras. Scope as a separate sub-project (~3 months field survey + calibration work).

### Blockchain / SBT Citizen Reputation

Polygon SBT for JAKI citizen reputation points is over-engineering for v1. The `citizen_points` database table provides equivalent functionality. Blockchain implementation is a Phase 4+ consideration.

---

## 18. Open Questions & Assumptions

### 18.1 Open Questions Requiring DISHUB Clarification

| ID | Question | Domain | Impact |
|---|---|---|---|
| OQ-01 | E-TLE API specification and sandbox endpoint? | E-TLE Integration | Blocking for FR-ETLE-01–05. Use mock spec until resolved. |
| OQ-02 | Sample CCTV footage from 5+ camera types for ANPR calibration? | ANPR Accuracy | High impact on KPI-02 |
| OQ-03 | GeoJSON for no-parking zones and busway corridors from DISHUB GIS? | Zone Configuration | Will self-digitize from public maps if not provided |
| OQ-04 | Legal standing of AI-generated evidence under Jakarta traffic law? | Legal | Critical for production deployment scope |
| OQ-05 | Jetson Orin edge nodes available, or cloud-only for demo? | Hardware | Affects latency KPIs (3s vs 5s target) |
| OQ-06 | DISHUB CRM webhook or polling API + authentication method? | CRM Integration | FR-VIO-08 |
| OQ-07 | Official relevant-unit routing taxonomy for each violation type? | Operations | Needed to replace generic unit labels in simulator and dispatch workflow |
| OQ-08 | Which pilot cameras are enforcement-grade for plate capture vs analytics-only? | ANPR/E-TLE | Needed for camera readiness calibration and E-TLE claims |

### 18.2 Assumptions

- **ASS-01**: YOLO26 AGPL-3.0 is acceptable for competition prototype. Production deployment requires Ultralytics Enterprise License.
- **ASS-02**: Violation thresholds (e.g., 30s for illegal parking) are configurable defaults, calibrated during trial phase.
- **ASS-03**: Human-in-the-loop E-TLE approval is a feature, not a limitation. Fully autonomous ticketing is explicitly out of scope v1.
- **ASS-04**: Balitower HLS streams are used for training data as competition research only. Written clearance sought before production.
- **ASS-05**: Zone GeoJSON for pilot corridors manually digitized from public maps if DISHUB GIS is unavailable.
- **ASS-06**: All government API integrations (Korlantas, SAMSAT, Dukcapil) are MOCK/STUB for demo. `USE_MOCK_APIS=true` is the default in all `.env` files.
- **ASS-07**: `combined_confidence` weight α=0.6 is an initial estimate. Calibration against labeled validation data required during trial phase before production use in enforcement.

---

## 19. Glossary

| Term | Definition |
|---|---|
| ANPR | Automatic Number Plate Recognition |
| ATCS | Area Traffic Control System |
| BoxMOT (BoT-SORT + OSNet ReID) | Multi-object tracking: all-detection association + appearance ReID |
| CLAHE | Contrast Limited Adaptive Histogram Equalization |
| DBSCAN | Density-Based Spatial Clustering of Applications with Noise |
| E-TLE | Electronic Traffic Law Enforcement |
| H3 | Uber's Hexagonal Hierarchical Spatial Index |
| JSEP | Jakarta Smart Enforcement Platform |
| MCLP | Maximum Coverage Location Problem |
| NMS | Non-Maximum Suppression (eliminated in YOLO26) |
| OSNet | Omni-Scale Network — lightweight ReID backbone (2.2MB) |
| PaddleOCR | PaddlePaddle OCR library — primary ANPR character recognition |
| STAL | Small-Target-Aware Label Assignment (YOLO26 training feature) |
| YOLO26 | You Only Look Once v26 — Ultralytics detection model (Q1 2026) |

---

## 20. Appendix

### 20.1 H3 Resolution Reference (CORRECTED from v4)

> JSEP uses **H3 Resolution 10** as the operational dashboard default and **Resolution 9** as the executive rollup.  
> **v4 error**: confused H3 cell edge length with cell area. Resolution 9 area is ~105,333 m², while Resolution 10 area is ~15,048 m².

| Resolution | Avg Cell Area | Avg Edge Length (H3 4.x) | Cells in Jakarta (~660 km²) |
|---|---|---|---|
| 7 | ~5,161,293 m² (5.16 km²) | ~1,406 m | ~128 cells |
| 8 | ~737,328 m² (0.74 km²) | ~531 m | ~895 cells |
| **9** | **~105,333 m² (0.105 km²)** | **~201 m** | **~6,266 cells** |
| **10** | **~15,048 m² (0.015 km²)** | **~76 m** | **~43,860 cells** |
| 11 | ~2,150 m² | ~29 m | ~307,000 cells |

KDE bandwidth should be calibrated in meters after projecting camera/event coordinates to a Jakarta-appropriate metric CRS. Initial competition setting: **300–600 m** smoothing for operational hotspots, with Resolution 10 as the operator default and Resolution 9 as the executive rollup.

### 20.2 Key References

- YOLO26: https://docs.ultralytics.com/models/yolo26 (fallback: https://docs.ultralytics.com/models/yolo11)
- BoxMOT: https://github.com/mikel-brostrom/boxmot
- PaddleOCR / PP-OCR: https://github.com/PaddlePaddle/PaddleOCR
- Real-ESRGAN: https://github.com/xinntao/Real-ESRGAN
- H3 cell statistics: https://h3geo.org/docs/core-library/restable/
- H3 Python bindings: https://h3geo.org/ | pip install h3
- Gemini model lifecycle: https://ai.google.dev/gemini-api/docs/deprecations
- PuLP: https://coin-or.github.io/pulp/
- MapLibre GL JS: https://maplibre.org/maplibre-gl-js/
- TimescaleDB: https://www.timescale.com/
- Roboflow Indonesian Plates: https://universe.roboflow.com → search "indonesia license plate"
- CVAT (free annotation tool): https://cvat.ai
- UU PDP: UU No. 27 Tahun 2022
- Pergub DKI 155/2018 (Ganjil-Genap schedule)
- OpenCV docs: https://docs.opencv.org

### 20.3 Document Change Log

| Version | Date | Change Summary |
|---|---|---|
| 1.0.0–4.0.0 | May 2026 | Initial through v4 drafts |
| **5.0.0** | **May 2026** | **Audit-driven revision: H3 area corrected (174m²→105,000m²), section numbers fixed, YOLO26 naming standardized, ERP/blockchain/Dukcapil face-match removed to Future Roadmap, government APIs marked MOCK, citizen points moved to DB, NarrativeAgent FR added with fallback, ANPR regex extended, confidence weights marked configurable, OpenCV augmentation pipeline added, Demo Scope section added, Resource Plan added** |
| **5.1.0** | **May 2026** | **Competition-focus audit: added fit guardrails, core violation demo alignment, CRM/JAKI classifier and unit routing, camera readiness scoring, CRM/dispatch database tables, H3 Resolution 10 operator default with Resolution 9 rollup, PaddleOCR/PP-OCR version correction, Gemini model/embedding update, and Ganjil-Genap/RAG demotion to stretch** |
| **5.1.1** | **May 2026** | **Clarified RAG/LLM split: deterministic legal/sanction reference layer is core v1; LLM/RAG remains optional for prose drafting only. Added FR-LEGAL-01, legal reference schema, and demo-scope legal/sanction lookup.** |
| **5.1.2** | **May 2026** | **Clarified Gemini and Docker posture: Gemini API can be enabled for optional assistive drafting, while Docker Desktop is not required. Docker Build Cloud is for image builds only; runtime may use local Docker Engine, remote VM, Kubernetes/Cloud Run, or managed services.** |
| **5.1.3** | **May 2026** | **Clarified swarm-agent posture: no separate swarm framework in v1; Kafka services already provide autonomous processing. Added optional read-only AI Insight Agent using Gemini over deterministic violation clusters.** |

---

*JSEP PRD v5.1.3 — Competition-Focused Audit Revision — AI Open Innovation Challenge 2026 — DISHUB DKI Jakarta*  
*Status: **AGENT-READY** — Core case requirements foregrounded — Safe for AI agent handoff*
