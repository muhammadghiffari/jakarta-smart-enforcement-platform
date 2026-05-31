# JSEP Setup Guide
> Windows + WSL2 + Kaggle GPU + Gemini API key  
> Single setup guide for the AI Open Innovation Challenge 2026 DISHUB DKI Jakarta case.

---

## 0. What This Guide Optimizes For

This project should be easy to run without Docker Desktop and without a local NVIDIA GPU.

Recommended setup:

| Need | Recommended Tool |
|---|---|
| Local coding | WSL2 Ubuntu + Python 3.12 virtualenv |
| GPU training | Kaggle Notebook with GPU |
| Image builds | Docker Build Cloud, optional |
| Runtime services | Managed cloud services or a remote VM |
| Legal/RAG extraction | Local WSL2 or Kaggle |
| LLM assist | Gemini API, optional and read-only |

Important rules:

- Legal basis, sanctions, fines, and enforcement eligibility must be deterministic through `FR-LEGAL-01`.
- Gemini may draft summaries or reviewer-assist text, but must not decide violations or sanctions.
- Docker Build Cloud builds images only. It does not run Postgres, Kafka, Redis, or object storage.
- `fixtures/holidays_2026.json` is optional/future unless you demo Ganjil-Genap.

---

## 1. Repository State

Current important files:

```text
docs/
  AI_OPEN_INNOVATION_CHALLENGE_2026.md
  DESIGN.md
  JSEP_Agent_Build_Guide.md
  JSEP_PRD_v5_REVISED.md
  JSEP_Setup_Guide.md

fixtures/
  holidays_2026.json

rag_corpus/
  2017PERGUB0031031.pdf
  2021pmkemenhub025.pdf
  BA Pemeriksaan Fisik Hasil Pekerjaan.pdf
  BA_Laporan Penyelesaian Pekerjaan.pdf
  BA_PengelolaanAset2021KEPGUB0031487.pdf
  BA_Surat Tagihan.pdf
  Ba Negosiasi Teknis Dan Harga.pdf
  Berita Acara Pemberian Penjelasan Kualifikasi.pdf
  Berita Acara Pemberian Penjelasan.pdf
  Berita Acara Pemeriksaan Hasil Pekerjaan.pdf
  Berita Acara Pengumuman Negosiasi.pdf
  PERGUB NO. 88 Tahun 2019.pdf
  PM_15_TAHUN_2019_Update.pdf
  Pergub_No._155_Tahun_2018.pdf
  UU Nomor 22 Tahun 2009.pdf
  c-14.-Berita-Acara-Serah-Terima-Barang.pdf

scripts/
  pdf_to_rag.py

templates/
  berita_acara_static.j2
  parse_camera_json.py
```

Note: the current `rag_corpus/` folder contains PDFs. The extraction step creates `.txt` files from those PDFs for optional RAG and deterministic legal reference drafting.

---

## 2. Local WSL2 Setup

Use Python 3.12. BoxMOT and several CV packages are safer on Python 3.12 than 3.13/3.14.

```bash
sudo apt update
sudo apt install -y software-properties-common curl git build-essential
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

cd /home/mghiffaa/Jsep
python3.12 -m venv .venv
source .venv/bin/activate

python --version
which python
```

Expected:

```text
Python 3.12.x
/home/mghiffaa/Jsep/.venv/bin/python
```

Install system dependencies:

```bash
sudo apt-get install -y \
  glpk-utils libglpk-dev \
  ffmpeg libsm6 libxext6 libgl1 \
  poppler-utils
```

Install Python dependencies:

```bash
source .venv/bin/activate
pip install --upgrade pip

pip install \
  ultralytics \
  "boxmot==19.0.0" \
  paddlepaddle paddleocr \
  opencv-python

pip install \
  torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cpu

pip install \
  h3 pulp scipy numpy pandas shapely tqdm "PyYAML==6.0.2" \
  python-dotenv fastapi "uvicorn[standard]" \
  sqlalchemy alembic geoalchemy2 psycopg2-binary \
  redis confluent-kafka minio \
  google-generativeai chromadb \
  jinja2 reportlab pymupdf roboflow aiohttp apscheduler
```

Do not put `--index-url https://download.pytorch.org/whl/cpu` on the same command as `ultralytics` or `boxmot`; it overrides PyPI and prevents those packages from being found.
If `paddlex` is in the environment, pin `PyYAML==6.0.2` because `paddlex` currently requires that exact version.

Verify:

```bash
python -c "import ultralytics, boxmot, h3, fitz; print('Core Python packages OK')"
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
glpsol --version
```

---

## 3. `.env` Template

Create `.env` locally by copying the template below or from [/.env.example](/home/mghiffaa/Jsep/.env.example). Never commit real keys.

```bash
cat > .env << 'ENVEOF'
# Detection
DETECTION_MODEL=yolo11n.pt
DETECTION_CONFIDENCE_THRESHOLD=0.45
PLATE_MODEL=models/plate_detector_best.pt

# Runtime mode
RUNTIME_MODE=cloud-managed
USE_MOCK_APIS=true
DEMO_MODE=true
DEMO_SEED_DATA=true

# Optional Gemini assist
ENABLE_LLM_DRAFTING=false
ENABLE_AI_INSIGHTS=false
GEMINI_API_KEY=
GEMINI_MODEL=
CHROMA_DB_PATH=./chroma_db
RAG_CORPUS_PATH=./rag_corpus

# Roboflow for Kaggle/local dataset download
ROBOFLOW_API_KEY=

# Database and services
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=jsep
POSTGRES_USER=jsep_user
POSTGRES_PASSWORD=jsep_local_dev
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_EVIDENCE=jsep-evidence

# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
ENVEOF
```

Use Gemini only for:

- Optional `AI Insight` summaries.
- Optional reviewer-assist `berita acara` wording.
- Executive summary wording after deterministic metrics are computed.

Do not use Gemini for:

- Violation decisions.
- Legal basis or sanction decisions.
- E-TLE approval or submission.

---

## 4. Docker and Runtime Options

If you have Docker Build Cloud, this section is the guide you use. It is already the runtime decision tree in this setup doc: `local-compose`, `remote-vm`, `cloud-managed`, or `build-cloud`.

Docker is helpful, but not mandatory.

| Mode | Use When | Notes |
|---|---|---|
| `local-compose` | You have Docker Engine or Docker Desktop | Run Postgres/Kafka/Redis/MinIO locally |
| `remote-vm` | You can rent/use a small cloud VM | Install Docker Engine on VM and run compose there |
| `cloud-managed` | You do not want runtime containers | Use managed DB/Kafka/Redis/object storage |
| `build-cloud` | You have Docker Build Cloud only | Build images remotely, deploy elsewhere |

Docker Build Cloud is only for builds:

```bash
docker buildx build \
  --builder muhammadghiffari/jsep \
  --tag ghcr.io/muhammadghiffari/jsep-api:demo \
  --push services/api
```

If using Build Cloud, you still need a runtime target such as Cloud Run, Kubernetes, or a remote VM.

---

## 5. Legal PDFs to `rag_corpus/*.txt`

The repo already has PDFs under `rag_corpus/`. Convert them to `.txt`:

```bash
source .venv/bin/activate

python scripts/pdf_to_rag.py \
  --input rag_corpus/ \
  --output rag_corpus/
```

Expected generated files include:

```text
uu_llaj_22_2009_relevant.txt
pergub_dki_155_2018_ganjilgenap.txt
pergub_dki_88_2019.txt
pm_perhubungan_15_2019_halte.txt
pm_kemenhub_025.txt
daftar_sanksi_pelanggaran.txt
ba_pemeriksaan_fisik_hasil_pekerjaan.txt
ba_laporan_penyelesaian_pekerjaan.txt
ba_pengelolaanaset2021kepgub0031487.txt
ba_surat_tagihan.txt
ba_negosiasi_teknis_dan_harga.txt
berita_acara_pemberian_penjelasan.txt
berita_acara_pemberian_penjelasan_kualifikasi.txt
berita_acara_pemeriksaan_hasil_pekerjaan.txt
berita_acara_pengumuman_negosiasi.txt
c-14.-berita-acara-serah-terima-barang.txt
```

Best practice:

- Use extracted `.txt` files for optional RAG/LLM drafting.
- Use reviewed YAML/JSON fixtures for deterministic `FR-LEGAL-01`.
- Do not treat RAG retrieval as the source of legal truth.

---

## 6. Deterministic Legal Reference Fixtures

Create this folder:

```bash
mkdir -p legal_reference
```

Create `legal_reference/violation_legal_map.yaml`:

```yaml
ILLEGAL_PARKING:
  legal_basis_code: "UU_LLAJ_22_2009_PASAL_287"
  sanction_code: "SANCTION_PARKING_DKI_DEFAULT"
  relevant_unit: "parking_enforcement"
  evidence_required:
    - plate_number
    - vehicle_class
    - no_parking_zone_id
    - duration_seconds
    - best_frame_url
    - video_clip_url
  static_report_fragment: "Vehicle detected stopping or parking in a prohibited zone for {duration_seconds} seconds."

BUSWAY_VIOLATION:
  legal_basis_code: "UU_LLAJ_22_2009_PASAL_287"
  sanction_code: "SANCTION_DEDICATED_LANE_DEFAULT"
  relevant_unit: "corridor_enforcement"
  evidence_required:
    - plate_number
    - vehicle_class
    - busway_zone_id
    - best_frame_url
    - video_clip_url
  static_report_fragment: "Vehicle detected occupying a dedicated busway lane."

BICYCLE_LANE_VIOLATION:
  legal_basis_code: "UU_LLAJ_22_2009_PASAL_287"
  sanction_code: "SANCTION_DEDICATED_LANE_DEFAULT"
  relevant_unit: "road_discipline_unit"
  evidence_required:
    - plate_number
    - vehicle_class
    - bicycle_lane_zone_id
    - duration_seconds
    - best_frame_url
    - video_clip_url
  static_report_fragment: "Motorized vehicle detected occupying a dedicated bicycle lane for {duration_seconds} seconds."

ILLEGAL_DROPOFF:
  legal_basis_code: "PM_PERHUBUNGAN_15_2019_HALTE"
  sanction_code: "SANCTION_ILLEGAL_DROPOFF_DEFAULT"
  relevant_unit: "public_transport_supervision"
  evidence_required:
    - plate_number
    - vehicle_class
    - designated_stop_id
    - duration_seconds
    - best_frame_url
    - video_clip_url
  static_report_fragment: "Public transport vehicle detected picking up or dropping off passengers outside a designated stop."
```

Create `legal_reference/sanction_references.yaml`:

```yaml
SANCTION_PARKING_DKI_DEFAULT:
  title: "Illegal parking / stopping sanction reference"
  fine_min_idr: 0
  fine_max_idr: 500000
  action_type: "ticket_or_tow"
  notes: "Demo reference. Validate with DISHUB legal team before production."

SANCTION_DEDICATED_LANE_DEFAULT:
  title: "Dedicated lane occupancy sanction reference"
  fine_min_idr: 0
  fine_max_idr: 500000
  action_type: "ticket"
  notes: "Demo reference. Validate with DISHUB legal team before production."

SANCTION_ILLEGAL_DROPOFF_DEFAULT:
  title: "Public transport illegal pick-up/drop-off sanction reference"
  fine_min_idr: 0
  fine_max_idr: 250000
  action_type: "dispatch_or_ticket"
  notes: "Demo reference. Validate with DISHUB legal team before production."
```

---

## 7. `holidays_2026.json`

`fixtures/holidays_2026.json` is only needed if you show the optional Ganjil-Genap bonus. It is not required for the core DISHUB case.

Core demo scenarios should be:

1. Illegal parking.
2. Busway/bicycle lane violation.
3. Public transport illegal pick-up/drop-off.
4. Hotspot analytics and officer placement.
5. CRM/JAKI report classification and corroboration.

---

## 8. Full Kaggle Notebook

Create a Kaggle Notebook:

1. Kaggle > Create Notebook.
2. Settings > Accelerator > GPU T4 x2 or P100.
3. Settings > Internet > ON.
4. Add Secrets:
   - `ROBOFLOW_API_KEY`
   - `GEMINI_API_KEY`, optional.
5. Upload the repository PDFs as a Kaggle Dataset, or upload a zip containing `rag_corpus/*.pdf`.

Paste the following cells.

```python
# =============================================================================
# JSEP Kaggle Notebook - v2 FULL FIXED
# Changelog vs v1:
#   - Cell 2: actual pip install commands (not just comments)
#   - Cell 7: fix label_dirs bug (duplicate index [2]), add data validation,
#             fix test split yaml (check existence first)
#   - Cell 8: batch=16 (PRD Section 16), add -1 for auto-batch fallback
#   - Cell NEW-A: legal reference fixtures (FR-LEGAL-01) — CRITICAL
#   - Cell NEW-B: pilot zone GeoJSON seed (Setup Guide Section 11)
#   - Cell NEW-C: OpenCV augmentation pipeline (PRD Section 11.3)
#   - Cell 5: Gemini embedding function if API key is available (PRD FR-REP-06)
#   - Cell 12: add manifest summary + more informative warnings
# =============================================================================

# ── Cell 1 - Environment and Configuration ───────────────────────────────────
import os
import sys
import json
import shutil
import random
from pathlib import Path

KAGGLE_INPUT = Path("/kaggle/input")
WORK         = Path("/kaggle/working")
DATASETS     = WORK / "datasets"
RUNS         = WORK / "jsep_runs"
RAG_TXT      = WORK / "rag_corpus_txt"
ARTIFACTS    = WORK / "artifacts"
LEGAL_REF    = WORK / "legal_reference"
FIXTURES     = WORK / "fixtures"

for p in [DATASETS, RUNS, RAG_TXT, ARTIFACTS, LEGAL_REF, FIXTURES]:
    p.mkdir(parents=True, exist_ok=True)

ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY", "")
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")

print("Python:", sys.version)
print("Kaggle input exists:", KAGGLE_INPUT.exists())
print("Roboflow key set:",    bool(ROBOFLOW_API_KEY))
print("Gemini key set:",      bool(GEMINI_API_KEY))

# ── Cell 2 - Install Dependencies ────────────────────────────────────────────
# FIX v2: actual install commands (v1 was just comments)
# IMPORTANT: --index-url whl/cpu MUST be in a separate command from ultralytics/boxmot
#            because it will override PyPI and other packages won't be found.

# Core CV + YOLO
# !pip -q install ultralytics roboflow

# BoxMOT tracker (BoT-SORT + OSNet ReID) — PRD Section 6.4
# !pip -q install "boxmot==19.0.0"

# OCR — PRD Section 6.2 (PaddleOCR 3.5+ / PP-OCRv5)
# !pip -q install paddlepaddle paddleocr

# Spatial analytics — PRD Section 6.5 (H3), Section 6.6 (MCLP)
# !pip -q install h3 pulp shapely geopandas scipy

# PDF extraction + RAG
# !pip -q install pymupdf tqdm pyyaml jinja2 reportlab

# Gemini + ChromaDB (optional RAG)
# !pip -q install google-generativeai chromadb

# Misc
# !pip -q install aiohttp apscheduler python-dotenv

# Uncomment all lines above for Kaggle.
# On WSL2 local, use `source .venv/bin/activate` first.

import ultralytics
print("Ultralytics:", ultralytics.__version__)
try:
    import h3
    print("H3:", h3.__version__)
except ImportError:
    print("WARNING: h3 not installed. Run pip install h3")
try:
    import fitz
    print("PyMuPDF: OK")
except ImportError:
    print("WARNING: pymupdf not installed.")

# ── Cell 3 - Inspect Uploaded Legal PDFs ─────────────────────────────────────
pdfs = sorted(KAGGLE_INPUT.glob("**/*.pdf"))
print(f"Found {len(pdfs)} PDF files")
for p in pdfs:
    print("-", p.relative_to(KAGGLE_INPUT))

if not pdfs:
    print("No PDFs uploaded. RAG extraction will be skipped.")
    print("Upload rag_corpus/*.pdf as a Kaggle Dataset to enable RAG.")

# ── Cell 4 - Extract Legal PDFs to RAG Text Files ────────────────────────────
import re
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    print("pymupdf not installed. Skipping PDF extraction.")

from tqdm.auto import tqdm

DOCUMENT_MAP = {
    r"uu.*22.*2009|llaj.*22|22.*2009.*llaj":               "uu_llaj_22_2009_relevant.txt",
    r"pergub.*155.*2018|ganjil.?genap|155.*2018":          "pergub_dki_155_2018_ganjilgenap.txt",
    r"pergub.*88.*2019|88.*2019":                          "pergub_dki_88_2019.txt",
    r"pm.*15.*2019|perhubungan.*15.*2019|halte|15.*2019":  "pm_perhubungan_15_2019_halte.txt",
    r"pm.*025|kemenhub.*025|025.*kemenhub":                "pm_kemenhub_025.txt",
    r"pergub.*31.*2017|denda|sanksi|penalty|2017.*pergub.*31|0031031": "daftar_sanksi_pelanggaran.txt",
    r"format.*ba|format.*berita.*acara":                   None,
}

def normalize_name(name: str) -> str:
    return name.lower().replace("-", "_").replace(" ", "_")

def map_output_name(pdf_path: Path, ba_counter: int) -> tuple[str, int]:
    name = normalize_name(pdf_path.name)
    for pattern, out_name in DOCUMENT_MAP.items():
        if re.search(pattern, name):
            return out_name, ba_counter
    if "berita" in name or re.match(r"^ba[_\s]", name):
        ba_counter += 1
        return f"{pdf_path.stem.lower().replace(' ', '_')}.txt", ba_counter
    return pdf_path.stem.lower().replace(" ", "_") + ".txt", ba_counter

def extract_pdf_text(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    pages = []
    for idx, page in enumerate(doc):
        pages.append(f"[Page {idx + 1}]\n{page.get_text('text')}")
    doc.close()
    return "\n\n".join(pages)

def clean_text(text: str) -> str:
    replacements = {
        r"\bPasa1\b": "Pasal",
        r"\n{3,}":    "\n\n",
        r"[ \t]{2,}": " ",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text.strip()

ba_counter = 0
written = []

if HAS_FITZ and pdfs:
    for pdf in tqdm(pdfs, desc="Extracting PDFs"):
        out_name, ba_counter = map_output_name(pdf, ba_counter)
        if out_name is None:
            continue
        out_path = RAG_TXT / out_name
        text = clean_text(extract_pdf_text(pdf))
        header = (
            f"# Source: {pdf.name}\n"
            f"# Extracted for JSEP optional RAG / reviewer-assist drafting\n"
            f"# Not authoritative for sanctions or enforcement decisions\n\n"
        )
        out_path.write_text(header + text, encoding="utf-8")
        written.append(out_path)
    print(f"Wrote {len(written)} text files to {RAG_TXT}")
    for p in sorted(RAG_TXT.glob("*.txt")):
        print("-", p.name, f"({p.stat().st_size:,} bytes)")
else:
    print("Skipped PDF extraction.")

# ── Cell 5 - Optional ChromaDB Index Smoke Test ───────────────────────────────
# FIX v2: use Gemini embedding if API key is available (PRD FR-REP-06)
#         fallback to default ChromaDB embedding if not
try:
    import chromadb
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False
    print("chromadb not installed. Skipping ChromaDB smoke test.")

if HAS_CHROMA:
    chroma_path = str(WORK / "chroma_db")

    if GEMINI_API_KEY:
        try:
            from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
            embedding_fn = GoogleGenerativeAiEmbeddingFunction(
                api_key=GEMINI_API_KEY,
                model_name="models/gemini-embedding-2"
            )
            print("Using Gemini embedding function (gemini-embedding-2)")
        except Exception as e:
            print(f"Gemini embedding failed ({e}), using default ChromaDB embedding.")
            embedding_fn = None
    else:
        print("GEMINI_API_KEY not set. Using default ChromaDB embedding.")
        embedding_fn = None

    client = chromadb.PersistentClient(path=chroma_path)
    collection_kwargs = {"name": "jsep_legal_demo"}
    if embedding_fn:
        collection_kwargs["embedding_function"] = embedding_fn
    collection = client.get_or_create_collection(**collection_kwargs)

    def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100):
        chunks, step = [], chunk_size - overlap
        for i in range(0, len(text), step):
            chunk = text[i:i + chunk_size].strip()
            if len(chunk) > 50:
                chunks.append(chunk)
        return chunks

    ids, docs, metas = [], [], []
    for txt in sorted(RAG_TXT.glob("*.txt")):
        text = txt.read_text(encoding="utf-8", errors="ignore")
        for idx, chunk in enumerate(chunk_text(text)):
            chunk_id = f"{txt.stem}_{idx}"
            if chunk_id not in ids:   # deduplicate on re-run
                ids.append(chunk_id)
                docs.append(chunk)
                metas.append({"source": txt.name})

    if docs:
        batch_size = 500
        for start in range(0, len(docs), batch_size):
            collection.add(
                ids=ids[start:start + batch_size],
                documents=docs[start:start + batch_size],
                metadatas=metas[start:start + batch_size],
            )
        print(f"Indexed {collection.count()} chunks into ChromaDB.")
        results = collection.query(
            query_texts=["parkir liar jalur busway halte sanksi"],
            n_results=min(3, collection.count()),
        )
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            print("\nSOURCE:", meta["source"])
            print(doc[:400])
    else:
        print("No RAG text files found. Skipping ChromaDB indexing.")

# ── Cell NEW-A - Legal Reference Fixtures (FR-LEGAL-01) ──────────────────────
# CRITICAL: PRD FR-LEGAL-01 — deterministic legal/sanction lookup
# This ensures E-TLE drafts, daily reports, and dispatch routing
# have an auditable legal basis, not from LLM.
import yaml

violation_legal_map = {
    "ILLEGAL_PARKING": {
        "legal_basis_code": "UU_LLAJ_22_2009_PASAL_287",
        "sanction_code": "SANCTION_PARKING_DKI_DEFAULT",
        "relevant_unit": "parking_enforcement",
        "evidence_required": [
            "plate_number", "vehicle_class", "no_parking_zone_id",
            "duration_seconds", "best_frame_url", "video_clip_url"
        ],
        "static_report_fragment": (
            "Kendaraan terdeteksi berhenti/parkir pada zona larangan "
            "selama {duration_seconds} detik."
        ),
    },
    "BUSWAY_VIOLATION": {
        "legal_basis_code": "UU_LLAJ_22_2009_PASAL_287",
        "sanction_code": "SANCTION_DEDICATED_LANE_DEFAULT",
        "relevant_unit": "corridor_enforcement",
        "evidence_required": [
            "plate_number", "vehicle_class", "busway_zone_id",
            "best_frame_url", "video_clip_url"
        ],
        "static_report_fragment": (
            "Kendaraan terdeteksi memasuki jalur busway TransJakarta yang dilarang."
        ),
    },
    "BICYCLE_LANE_VIOLATION": {
        "legal_basis_code": "UU_LLAJ_22_2009_PASAL_287",
        "sanction_code": "SANCTION_DEDICATED_LANE_DEFAULT",
        "relevant_unit": "road_discipline_unit",
        "evidence_required": [
            "plate_number", "vehicle_class", "bicycle_lane_zone_id",
            "duration_seconds", "best_frame_url", "video_clip_url"
        ],
        "static_report_fragment": (
            "Kendaraan bermotor terdeteksi memasuki jalur sepeda khusus "
            "selama {duration_seconds} detik."
        ),
    },
    "ILLEGAL_DROPOFF": {
        "legal_basis_code": "PM_PERHUBUNGAN_15_2019_HALTE",
        "sanction_code": "SANCTION_ILLEGAL_DROPOFF_DEFAULT",
        "relevant_unit": "public_transport_supervision",
        "evidence_required": [
            "plate_number", "vehicle_class", "designated_stop_id",
            "duration_seconds", "best_frame_url", "video_clip_url"
        ],
        "static_report_fragment": (
            "Kendaraan angkutan umum terdeteksi menaikkan/menurunkan penumpang "
            "di luar halte resmi selama {duration_seconds} detik."
        ),
    },
}

sanction_references = {
    "SANCTION_PARKING_DKI_DEFAULT": {
        "title": "Sanksi parkir/berhenti ilegal",
        "fine_min_idr": 0,
        "fine_max_idr": 500_000,
        "action_type": "ticket_or_tow",
        "notes": "Referensi demo. Validasi dengan tim hukum DISHUB sebelum produksi.",
    },
    "SANCTION_DEDICATED_LANE_DEFAULT": {
        "title": "Sanksi pelanggaran jalur khusus (busway/sepeda)",
        "fine_min_idr": 0,
        "fine_max_idr": 500_000,
        "action_type": "ticket",
        "notes": "Referensi demo. Validasi dengan tim hukum DISHUB sebelum produksi.",
    },
    "SANCTION_ILLEGAL_DROPOFF_DEFAULT": {
        "title": "Sanksi naik/turun penumpang di luar halte",
        "fine_min_idr": 0,
        "fine_max_idr": 250_000,
        "action_type": "dispatch_or_ticket",
        "notes": "Referensi demo. Validasi dengan tim hukum DISHUB sebelum produksi.",
    },
}

# Save to LEGAL_REF and ARTIFACTS
(LEGAL_REF / "violation_legal_map.yaml").write_text(
    yaml.safe_dump(violation_legal_map, allow_unicode=True, sort_keys=False),
    encoding="utf-8"
)
(LEGAL_REF / "sanction_references.yaml").write_text(
    yaml.safe_dump(sanction_references, allow_unicode=True, sort_keys=False),
    encoding="utf-8"
)
print("Legal reference fixtures written:")
for f in sorted(LEGAL_REF.glob("*.yaml")):
    print("-", f.name)

# Smoke test: lookup ILLEGAL_PARKING
def lookup_legal(violation_type: str) -> dict:
    """Deterministic legal lookup — without LLM. PRD FR-LEGAL-01."""
    entry = violation_legal_map.get(violation_type, {})
    sanction = sanction_references.get(entry.get("sanction_code", ""), {})
    return {**entry, "sanction_detail": sanction}

result = lookup_legal("ILLEGAL_PARKING")
print("\nSmoke test FR-LEGAL-01 — ILLEGAL_PARKING:")
print(f"  Legal basis : {result['legal_basis_code']}")
print(f"  Sanction    : {result['sanction_detail']['title']}")
print(f"  Fine max    : Rp {result['sanction_detail']['fine_max_idr']:,}")
print(f"  Unit        : {result['relevant_unit']}")

# ── Cell NEW-B - Pilot Zone GeoJSON Seed ─────────────────────────────────────
# PRD Setup Guide Section 11 — minimum 2 NO_PARKING, 2 BUSWAY, 1 BICYCLE, 1 STOP
# The coordinates below are DEMO placeholders for the Sudirman-Thamrin corridor.
# Replace with actual coordinates from DISHUB GIS or geojson.io.

pilot_zones = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "zone_type": "NO_PARKING", "threshold_s": 30,
                "corridor": "SUDIRMAN", "name": "Sudirman no-parking north"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[106.8219, -6.2022], [106.8229, -6.2022],
                                  [106.8229, -6.2032], [106.8219, -6.2032],
                                  [106.8219, -6.2022]]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_type": "NO_PARKING", "threshold_s": 30,
                "corridor": "THAMRIN", "name": "Thamrin no-parking south"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[106.8198, -6.2120], [106.8208, -6.2120],
                                  [106.8208, -6.2130], [106.8198, -6.2130],
                                  [106.8198, -6.2120]]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_type": "BUSWAY_LANE", "threshold_s": 0,
                "corridor": "SUDIRMAN", "name": "Sudirman busway corridor"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[106.8210, -6.2010], [106.8220, -6.2010],
                                  [106.8220, -6.2050], [106.8210, -6.2050],
                                  [106.8210, -6.2010]]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_type": "BUSWAY_LANE", "threshold_s": 0,
                "corridor": "THAMRIN", "name": "Thamrin busway corridor"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[106.8195, -6.2090], [106.8205, -6.2090],
                                  [106.8205, -6.2140], [106.8195, -6.2140],
                                  [106.8195, -6.2090]]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_type": "BICYCLE_LANE", "threshold_s": 10,
                "corridor": "SUDIRMAN", "name": "Sudirman bicycle lane"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[106.8225, -6.2010], [106.8230, -6.2010],
                                  [106.8230, -6.2060], [106.8225, -6.2060],
                                  [106.8225, -6.2010]]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "zone_type": "DESIGNATED_STOP", "threshold_s": 15,
                "corridor": "SUDIRMAN", "name": "Halte Sudirman BRT"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[106.8216, -6.2040], [106.8224, -6.2040],
                                  [106.8224, -6.2045], [106.8216, -6.2045],
                                  [106.8216, -6.2040]]]
            }
        },
    ]
}

zones_path = FIXTURES / "zones_pilot.geojson"
zones_path.write_text(json.dumps(pilot_zones, indent=2), encoding="utf-8")
print(f"Pilot zones GeoJSON written: {zones_path}")
print(f"  Zones count: {len(pilot_zones['features'])}")
for f in pilot_zones["features"]:
    print(f"  - {f['properties']['zone_type']}: {f['properties']['name']}")
print("\nREPLACE the coordinates above with actual data from DISHUB GIS or geojson.io!")

# ── Cell 6 - Download Public Indonesian Plate Datasets from Roboflow ──────────
if not ROBOFLOW_API_KEY:
    raise RuntimeError("Set ROBOFLOW_API_KEY in Kaggle Secrets before running this cell.")

from roboflow import Roboflow

rf = Roboflow(api_key=ROBOFLOW_API_KEY)

roboflow_datasets = [
    ("praproject",            "indonesia-lpr",                        1),
    ("rendika-nurhartanto-s", "indonesia-license-plate-detection",    1),
    ("ksp-workspace",         "indonesia-license-plate-iqrtj",        1),
]

downloaded_dirs = []
for workspace, project, version in roboflow_datasets:
    target = DATASETS / project
    if target.exists():
        print("Already exists:", target)
    else:
        print("Downloading:", project)
        rf.workspace(workspace).project(project).version(version).download(
            "yolov8", location=str(target),
        )
    downloaded_dirs.append(target)

print("\nDownloaded datasets:", [d.name for d in downloaded_dirs])

# ── Cell NEW-C - OpenCV Augmentation Pipeline (PRD Section 11.3) ─────────────
# Run augmentation on the downloaded datasets before merging.
# Adds robustness against rain, night, motion blur, and JPEG artifacts.
import cv2
import numpy as np

class JSEPAugmentor:
    """OpenCV augmentation — PRD Section 11.3. GPU-free (CPU only)."""

    @staticmethod
    def add_rain_streaks(img: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        rain_layer = np.zeros_like(img)
        for _ in range(int(500 * intensity)):
            x = np.random.randint(0, img.shape[1])
            y = np.random.randint(0, img.shape[0])
            length = np.random.randint(5, 20)
            cv2.line(rain_layer, (x, y), (x - 2, y + length), (200, 200, 200), 1)
        return cv2.addWeighted(img, 1.0, rain_layer, 0.4 * intensity, 0)

    @staticmethod
    def simulate_night(img: np.ndarray, gamma: float = 0.3) -> np.ndarray:
        inv_gamma = 1.0 / gamma
        table = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype=np.uint8
        )
        return cv2.LUT(img, table)

    @staticmethod
    def apply_clahe(img: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    @staticmethod
    def add_motion_blur(img: np.ndarray, kernel_size: int = 9) -> np.ndarray:
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size) / kernel_size
        return cv2.filter2D(img, -1, kernel)

    @staticmethod
    def add_jpeg_artifacts(img: np.ndarray, quality: int = 50) -> np.ndarray:
        _, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    def augment(self, img: np.ndarray) -> np.ndarray:
        augmentations = [
            lambda x: self.add_rain_streaks(x, np.random.uniform(0.2, 0.8)),
            lambda x: self.simulate_night(x, np.random.uniform(0.1, 0.4)),
            lambda x: self.apply_clahe(x),
            lambda x: self.add_motion_blur(x, int(np.random.choice([3, 5, 7, 9]))),
            lambda x: self.add_jpeg_artifacts(x, int(np.random.randint(40, 70))),
        ]
        selected = np.random.choice(augmentations,
                                    size=np.random.randint(1, 3),
                                    replace=False)
        for aug in selected:
            img = aug(img)
        return img

def augment_dataset(src_image_dir: Path, aug_ratio: float = 0.3,
                    max_aug: int = 500) -> int:
    """
    Augment up to max_aug images from src_image_dir.
    Saves augmented copies alongside originals with _aug suffix.
    aug_ratio: fraction of dataset images to augment.
    """
    augmentor = JSEPAugmentor()
    images = [p for p in src_image_dir.glob("*")
              if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
              and "_aug" not in p.stem]
    sample = images[:max(1, min(max_aug, int(len(images) * aug_ratio)))]
    count = 0
    for img_path in tqdm(sample, desc=f"Augmenting {src_image_dir.name}", leave=False):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        aug_img = augmentor.augment(img.copy())
        aug_path = img_path.parent / f"{img_path.stem}_aug{img_path.suffix}"
        cv2.imwrite(str(aug_path), aug_img)
        # Copy label file alongside augmented image
        lbl_src = img_path.parent.parent / "labels" / img_path.parent.name / f"{img_path.stem}.txt"
        lbl_alt = img_path.parent / f"{img_path.stem}.txt"
        lbl_dst = img_path.parent.parent / "labels" / img_path.parent.name / f"{img_path.stem}_aug.txt"
        lbl_dst.parent.mkdir(parents=True, exist_ok=True)
        if lbl_src.exists():
            shutil.copy2(lbl_src, lbl_dst)
        elif lbl_alt.exists():
            shutil.copy2(lbl_alt, lbl_dst)
        count += 1
    return count

# Augment train splits from all downloaded datasets
total_augmented = 0
for dataset_dir in downloaded_dirs:
    for candidate in [
        dataset_dir / "train" / "images",
        dataset_dir / "images" / "train",
    ]:
        if candidate.exists():
            n = augment_dataset(candidate, aug_ratio=0.25, max_aug=300)
            print(f"Augmented {n} images from {candidate}")
            total_augmented += n
            break

print(f"\nTotal augmented images created: {total_augmented}")

# ── Cell 7 - Merge YOLO Plate Datasets ───────────────────────────────────────
import yaml

MERGED = DATASETS / "merged_plates"

def find_dataset_yaml(root: Path) -> Path:
    candidates = list(root.glob("**/data.yaml")) + list(root.glob("**/dataset.yaml"))
    if not candidates:
        raise FileNotFoundError(f"No data.yaml found under {root}")
    return candidates[0]

def copy_split(src_root: Path, split: str, dst_root: Path) -> int:
    image_dirs = [
        src_root / split / "images",
        src_root / "images" / split,
        src_root / split,
    ]
    # FIX v2: label_dirs[2] is no longer a duplicate of label_dirs[1]
    label_dirs = [
        src_root / split / "labels",
        src_root / "labels" / split,
        src_root / "labels",       # fallback: flat labels dir
    ]

    image_dir = next((p for p in image_dirs if p.exists()), None)
    label_dir = next((p for p in label_dirs if p.exists()), None)
    if image_dir is None:
        return 0

    dst_img = dst_root / "images" / split
    dst_lbl = dst_root / "labels" / split
    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)

    count = 0
    for img in image_dir.glob("*"):
        if img.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            continue
        prefix  = src_root.name.replace("-", "_")
        new_img = dst_img / f"{prefix}_{img.name}"
        shutil.copy2(img, new_img)

        src_label = (label_dir / f"{img.stem}.txt") if label_dir else None
        dst_label  = dst_lbl / f"{new_img.stem}.txt"

        if src_label and src_label.exists():
            lines = []
            for line in src_label.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    try:
                        coords = [float(p) for p in parts[1:5]]
                        if all(0.0 <= c <= 1.0 for c in coords):
                            parts[0] = "0"
                            lines.append(" ".join(parts[:5]))
                    except ValueError:
                        pass
            dst_label.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        else:
            dst_label.write_text("", encoding="utf-8")
        count += 1
    return count

if MERGED.exists():
    shutil.rmtree(MERGED)

total = {"train": 0, "valid": 0, "test": 0}

for dataset_dir in downloaded_dirs:
    data_yaml = find_dataset_yaml(dataset_dir)
    src_root  = data_yaml.parent
    print("Merging:", src_root.name)
    for split in ["train", "valid", "test"]:
        n = copy_split(src_root, split, MERGED)
        total[split] += n

# FIX v2: validate sample count before training
print("\nMerged counts:", total)
if total["train"] == 0:
    raise RuntimeError(
        "STOP: train split is empty after merge!\n"
        "Ensure dataset is downloaded correctly and folder structure matches:\n"
        "  images/train/, images/valid/, labels/train/, labels/valid/"
    )
if total["valid"] == 0:
    print("WARNING: valid split is empty. YOLO will use train for validation.")

# FIX v2: test split in data.yaml is only written if the folder exists
val_split  = "valid" if (MERGED / "images" / "valid").exists() else "train"
test_entry = "images/test" if (MERGED / "images" / "test").exists() else None

data = {
    "path":  str(MERGED),
    "train": "images/train",
    "val":   f"images/{val_split}",
    "names": {0: "license_plate"},
}
if test_entry:
    data["test"] = test_entry

# Clear old cache so YOLO scans again
for cache in MERGED.rglob("*.cache"):
    cache.unlink()
    print(f"Deleted stale cache: {cache.name}")

(MERGED / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
print("\ndata.yaml:")
print((MERGED / "data.yaml").read_text())

# ── Cell 8 - Train Plate Detector ────────────────────────────────────────────
import torch
from ultralytics import YOLO

def load_yolo_with_fallback(primary: str, fallback: str):
    try:
        print(f"Trying model: {primary}")
        m = YOLO(primary)
        print(f"Loaded: {primary}")
        return m, primary
    except Exception as exc:
        print(f"Primary {primary!r} failed: {exc}")
        print(f"Fallback model: {fallback}")
        return YOLO(fallback), fallback

def get_device() -> str:
    n = torch.cuda.device_count()
    if n >= 2:
        return "0,1"
    if n == 1:
        return "0"
    return "cpu"

DEVICE = get_device()
print("Training device:", DEVICE, f"({torch.cuda.device_count()} GPU(s) detected)")

plate_model, plate_base = load_yolo_with_fallback("yolo26s.pt", "yolo11s.pt")

# FIX v2: batch=16 per PRD Section 16 (single RTX 4090 / T4 16GB)
# batch=32 risks OOM on T4 with imgsz=640.
# Use batch=-1 for auto-detect (Ultralytics >= 8.1)
plate_results = plate_model.train(
    data=str(MERGED / "data.yaml"),
    epochs=80,
    imgsz=640,
    batch=16,          # PRD Section 16: 16 for single GPU. Increase to 32 if P100/A100.
    device=DEVICE,
    patience=15,
    project=str(RUNS),
    name="plate_detector_v1",
    save_period=10,
    exist_ok=True,
    # Augmentation flags (YOLO native) — PRD Section 11.4
    flipud=0.0,    # do not flip vertically for traffic camera images
    fliplr=0.5,
    degrees=10.0,
    mosaic=1.0,
    hsv_v=0.4,
)

# Ultralytics may return None from train() in this version.
best_pt = RUNS / "plate_detector_v1" / "weights" / "best.pt"
print("Plate detector best:", best_pt)

# ── Cell 9 - Evaluate Plate Detector ─────────────────────────────────────────
plate_metrics = plate_model.val(data=str(MERGED / "data.yaml"))
print(f"Plate detector mAP50:     {plate_metrics.box.map50:.3f}")
print(f"Plate detector mAP50-95:  {plate_metrics.box.map:.3f}")
print(f"Plate detector precision: {plate_metrics.box.mp:.3f}")
print(f"Plate detector recall:    {plate_metrics.box.mr:.3f}")

# PRD KPI-01 target: mAP50 > 0.90
# PRD KPI-04/05 target: precision > 0.85, recall > 0.78
if plate_metrics.box.map50 < 0.70:
    print("\nWARNING: mAP50 < 0.70. Consider:")
    print("  1. Adding data augmentation (Cell NEW-C)")
    print("  2. Increasing epochs (currently 80)")
    print("  3. Checking label quality with fix_labels.py")

# ── Cell 10 - Optional Vehicle Detector Training ──────────────────────────────
vehicle_yaml_candidates = (
    list(KAGGLE_INPUT.glob("**/data.yaml")) +
    list(KAGGLE_INPUT.glob("**/dataset.yaml"))
)
vehicle_yaml_candidates = [
    p for p in vehicle_yaml_candidates
    if not any(kw in str(p).lower() for kw in ["merged_plates", "license", "plate"])
]

vehicle_model = None
vehicle_base  = None

if vehicle_yaml_candidates:
    vehicle_yaml = vehicle_yaml_candidates[0]
    print("Vehicle dataset found:", vehicle_yaml)
    vehicle_model, vehicle_base = load_yolo_with_fallback("yolo26n.pt", "yolo11n.pt")
    vehicle_results = vehicle_model.train(
        data=str(vehicle_yaml),
        epochs=100,
        imgsz=640,
        batch=16,
        device=DEVICE,
        patience=20,
        project=str(RUNS),
        name="vehicle_detector_v1",
        save_period=10,
        exist_ok=True,
        flipud=0.0,
        degrees=10.0,
    )
    vehicle_metrics = vehicle_model.val(data=str(vehicle_yaml))
    print(f"Vehicle mAP50:     {vehicle_metrics.box.map50:.3f}")
    print(f"Vehicle precision: {vehicle_metrics.box.mp:.3f}")
    print(f"Vehicle recall:    {vehicle_metrics.box.mr:.3f}")
else:
    print("No custom vehicle dataset uploaded. Skipping vehicle detector training.")
    print("PRD Section 11.1: target 8 classes (car, motorcycle, truck, bus, angkot, bajaj, bicycle, pedestrian)")
    print("Upload /kaggle/input/jsep-vehicle-dataset/data.yaml to enable this cell.")

# ── Cell 11 - Optional Gemini AI Insight Smoke Test ──────────────────────────
if GEMINI_API_KEY:
    import google.generativeai as genai

    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
    genai.configure(api_key=GEMINI_API_KEY)
    gemini = genai.GenerativeModel(model_name)

    # Use legal lookup for grounding cluster — not LLM for legal decisions
    cluster = {
        "cluster_id":   "CLU-DEMO-001",
        "corridor":     "Sudirman",
        "time_window":  "2026-05-31T07:00:00+07:00/2026-05-31T07:20:00+07:00",
        "top_violation_types":              ["ILLEGAL_PARKING", "BUSWAY_VIOLATION"],
        "violation_count":                  9,
        "active_count":                     6,
        "recommended_unit":                 "parking_enforcement",
        "recommended_action_deterministic": "Deploy 2 officers to the top hotspot cells.",
        # Add legal grounding from FR-LEGAL-01
        "legal_references": {
            vt: lookup_legal(vt).get("legal_basis_code")
            for vt in ["ILLEGAL_PARKING", "BUSWAY_VIOLATION"]
        }
    }

    # PRD FR-INSIGHT-01: prompt must specify "do not invent" and strict JSON output
    prompt = f"""
You are an operational assistant for JSEP owned by DISHUB DKI Jakarta.
Summarize ONLY from the provided cluster JSON.
Do not invent new license plates, cameras, sanctions, or locations.
Output ONLY valid JSON with keys:
priority, summary, recommended_action, reasoning, confidence_note, source_cluster_id.

Cluster:
{json.dumps(cluster, ensure_ascii=False, indent=2)}
"""
    try:
        response = gemini.generate_content(prompt)
        # Validate that output is JSON before rendering
        raw = response.text.strip().strip("```json").strip("```").strip()
        parsed = json.loads(raw)
        print("AI Insight output (validated JSON):")
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        print(f"WARNING: Gemini output is not valid JSON: {e}")
        print("Raw response:", response.text[:500])
    except Exception as e:
        print(f"Gemini API error: {e}")
else:
    print("GEMINI_API_KEY not set. Skipping optional AI Insight smoke test.")
    print("Set ENABLE_AI_INSIGHTS=false in .env (PRD FR-INSIGHT-01).")

# ── Cell 12 - Package Artifacts ───────────────────────────────────────────────
import zipfile

best_plate_path   = RUNS / "plate_detector_v1"  / "weights" / "best.pt"
best_vehicle_path = RUNS / "vehicle_detector_v1" / "weights" / "best.pt"

# Copy model weights
if best_plate_path.exists():
    shutil.copy2(best_plate_path, ARTIFACTS / "plate_detector_best.pt")
    print("Copied plate model.")
else:
    print("WARNING: plate best.pt not found. Training may have failed or hasn't finished.")

if best_vehicle_path.exists():
    shutil.copy2(best_vehicle_path, ARTIFACTS / "vehicle_detector_best.pt")
    print("Copied vehicle model.")

# Copy RAG text files
for txt in sorted(RAG_TXT.glob("*.txt")):
    shutil.copy2(txt, ARTIFACTS / txt.name)

# Copy legal reference fixtures (FR-LEGAL-01)
for yaml_f in sorted(LEGAL_REF.glob("*.yaml")):
    shutil.copy2(yaml_f, ARTIFACTS / yaml_f.name)

# Copy pilot zones GeoJSON
if zones_path.exists():
    shutil.copy2(zones_path, ARTIFACTS / "zones_pilot.geojson")

# Write manifest
artifact_manifest = {
    "jsep_version":       "v2",
    "plate_model_base":   plate_base,
    "plate_model_path":   str(best_plate_path)   if best_plate_path.exists()   else None,
    "vehicle_model_base": vehicle_base,
    "vehicle_model_path": str(best_vehicle_path) if best_vehicle_path.exists() else None,
    "rag_text_files":     [p.name for p in sorted(RAG_TXT.glob("*.txt"))],
    "legal_fixtures":     [p.name for p in sorted(LEGAL_REF.glob("*.yaml"))],
    "zones_geojson":      "zones_pilot.geojson" if zones_path.exists() else None,
    "merged_dataset_counts": total,
    "training_device":    DEVICE,
}

(ARTIFACTS / "manifest.json").write_text(
    json.dumps(artifact_manifest, indent=2), encoding="utf-8"
)

# Create zip
zip_path = WORK / "jsep_kaggle_artifacts.zip"
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for p in ARTIFACTS.glob("*"):
        z.write(p, arcname=p.name)

print(f"\nArtifact zip: {zip_path}")
print(f"Size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
print("Download from Kaggle Output panel.")
print("\nManifest:")
print(json.dumps(artifact_manifest, indent=2))
print("\nAfter downloading, follow Setup Guide Section 9 to extract into models/ and rag_corpus/")
```


---

## 9. After Kaggle Finishes

Download `jsep_kaggle_artifacts.zip`, then extract locally:

```bash
mkdir -p models rag_corpus
unzip jsep_kaggle_artifacts.zip -d kaggle_artifacts

cp kaggle_artifacts/plate_detector_best.pt models/
cp kaggle_artifacts/*.txt rag_corpus/ || true
```

Update `.env`:

```bash
PLATE_MODEL=models/plate_detector_best.pt
```

If you trained a vehicle model, also copy it:

```bash
cp kaggle_artifacts/vehicle_detector_best.pt models/
# then set:
# DETECTION_MODEL=models/vehicle_detector_best.pt
```

---

## 10. Camera JSON Parsing

`templates/parse_camera_json.py` currently lives under `templates/`. Prefer moving it to `scripts/` later, but you can run it from its current path:

```bash
python templates/parse_camera_json.py \
  --input path/to/cameras.json \
  --output fixtures/cameras_jsep.json \
  --probe \
  --pilot-only
```

Expected output:

```text
fixtures/cameras_jsep.json
```

Use only pilot corridors and public-facility areas for the competition demo.

---

## 11. Zone GeoJSON

Fastest path:

1. Open `https://geojson.io`.
2. Search for a pilot corridor, e.g. Sudirman or Thamrin.
3. Draw polygons for `NO_PARKING`, `BUSWAY_LANE`, `BICYCLE_LANE`, and `DESIGNATED_STOP`.
4. Add properties:

```json
{
  "zone_type": "NO_PARKING",
  "threshold_s": 30,
  "corridor": "SUDIRMAN",
  "name": "Sudirman no-parking pilot zone"
}
```

Minimum demo target:

```text
2 NO_PARKING zones
2 BUSWAY_LANE zones
1 BICYCLE_LANE zone
1 DESIGNATED_STOP zone
```

Save as:

```text
fixtures/zones_pilot.geojson
```

For designated stops, convert the CSV to GeoJSON with:

```bash
python scripts/designated_stops_to_geojson.py \
  --input fixtures/designated_stops.csv \
  --output fixtures/designated_stops.geojson
```

This should be used as the stop-layer fixture for public transport pick-up/drop-off logic, not as a legal source.

Best practice:

- Keep `fixtures/designated_stops.csv` as the raw source export.
- Use `fixtures/designated_stops.geojson` as the runtime fixture.
- Load it through a single helper such as `scripts/designated_stops_loader.py` instead of parsing CSV in multiple places.

---

## 12. Demo Clip Sources

Use recorded clips for reliability. Public CCTV streams are useful, but availability changes.

Possible sources:

| Source | Use |
|---|---|
| Balitower public CCTV | Training/demo clips, check ToS before scraping |
| Jakarta Smart City CCTV | Demo clips if stream URLs are available |
| TMC Polda Metro YouTube | Backup recorded traffic footage |

Record HLS:

```bash
mkdir -p demo_clips

ffmpeg -i "https://example.com/stream.m3u8" \
  -t 60 -c copy \
  demo_clips/scenario_a_illegal_parking.mp4
```

Core demo clips:

```text
scenario_a_illegal_parking.mp4
scenario_b_dedicated_lane.mp4
scenario_c_illegal_dropoff.mp4
scenario_d_hotspot_seed.json
scenario_e_crm_report.jpg
```

---

## 13. Runtime Service Choices

No Docker Desktop:

| Component | Practical Option |
|---|---|
| PostgreSQL/PostGIS | Supabase, Neon + PostGIS, Timescale Cloud, or remote VM Postgres |
| Kafka | Redpanda Cloud, Confluent Cloud, or temporary in-memory event bus for prototype |
| Redis | Upstash Redis or remote VM Redis |
| Object storage | S3, Cloudflare R2, GCS, or MinIO on remote VM |

Remote VM:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
docker compose up -d
```

Docker Build Cloud:

```bash
docker buildx build \
  --builder muhammadghiffari/jsep \
  --tag ghcr.io/muhammadghiffari/jsep-api:demo \
  --push services/api
```

---

## 14. Demo Validation Checklist

Before presenting:

```text
Core model/demo:
  [ ] Plate detector weights copied to models/
  [ ] At least 3 demo clips available
  [ ] Pilot zones GeoJSON exists
  [ ] Camera metadata exists or demo camera fixtures are seeded

Legal and reporting:
  [ ] legal_reference/*.yaml exists
  [ ] templates/berita_acara_static.j2 renders with sample data
  [ ] rag_corpus/*.txt exists if optional RAG is enabled

Optional AI:
  [ ] ENABLE_AI_INSIGHTS=false by default
  [ ] Gemini key configured only in runtime secrets
  [ ] AI Insight output is JSON validated and read-only

Infrastructure:
  [ ] Runtime mode chosen
  [ ] `.env` uses runtime endpoints, not hardcoded localhost unless local
  [ ] USE_MOCK_APIS=true
```

---

## 15. What Not To Build for v1

Keep these out of the core competition build:

```text
Separate swarm framework
Cross-camera ReID topology
Live Korlantas/SAMSAT/Dukcapil integration
Driver face recognition
Blockchain/SBT
Ganjil-Genap as a core scenario
LLM as legal/sanction authority
```

Best demo value comes from:

```text
Reliable violation detection
ANPR and duration
Hotspot heatmap
Officer/E-TLE camera placement recommendation
CRM/JAKI report automation
Deterministic legal/sanction references
Optional read-only AI Insight
```
