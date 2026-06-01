from __future__ import annotations

import os
import hashlib
from pathlib import Path

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


CORPUS_COLLECTION = "jsep_legal"
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_CHROMA_PATH = os.environ.get("CHROMA_DB_PATH", str(PROJECT_ROOT / "chroma_db"))


class HashEmbeddingFunction(EmbeddingFunction):
    """Deterministic local fallback embedding with no network/model download."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            vector = [0.0] * self.dimensions
            for token in str(text).lower().split():
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                idx = int.from_bytes(digest[:4], "big") % self.dimensions
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[idx] += sign
            norm = sum(v * v for v in vector) ** 0.5 or 1.0
            embeddings.append([v / norm for v in vector])
        return embeddings


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    step = max(1, chunk_size - overlap)
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if len(chunk) > 20:
            chunks.append(chunk)
    return chunks


def _get_collection():
    """Get or create the Chroma collection, avoiding EF conflict on existing collections."""
    client = chromadb.PersistentClient(path=DEFAULT_CHROMA_PATH)
    existing = [c.name for c in client.list_collections()]
    if CORPUS_COLLECTION in existing:
        # Collection already exists — fetch it without an EF to avoid conflict.
        # We embed manually via HashEmbeddingFunction only when adding/querying.
        return client.get_collection(name=CORPUS_COLLECTION)
    return client.create_collection(
        name=CORPUS_COLLECTION,
        embedding_function=HashEmbeddingFunction(),
    )


def index_legal_corpus(corpus_dir: str = "rag_corpus/") -> int:
    corpus_path = Path(corpus_dir)
    collection = _get_collection()
    ef = HashEmbeddingFunction()

    indexed = 0
    for doc_path in sorted(corpus_path.glob("*.txt")):
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        chunks = _chunk_text(text)
        ids = [f"{doc_path.stem}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": doc_path.name, "chunk_index": i} for i in range(len(chunks))]
        if chunks:
            embeddings = ef(chunks)
            collection.add(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
            indexed += len(chunks)

    print(f"Indexed {indexed} chunks into {CORPUS_COLLECTION}.")
    return indexed


def retrieve_legal_context(query: str, n_results: int = 5) -> list[str]:
    collection = _get_collection()
    # Compute the embedding manually since the persisted collection may not store an EF.
    ef = HashEmbeddingFunction()
    query_embedding = ef([query])
    try:
        results = collection.query(query_embeddings=query_embedding, n_results=n_results)
    except Exception:
        # If collection is empty, query will fail — return empty context gracefully.
        return []
    return results.get("documents", [[]])[0]


def generate_berita_acara(violation: dict) -> str:
    """
    Optional helper for review drafting.
    Falls back to the static template if Gemini is unavailable.
    """
    query = f"{violation.get('violation_type', '')} {violation.get('zone_name', '')} {violation.get('duration_s', '')}s Jakarta"
    legal_context = retrieve_legal_context(query, n_results=5)

    try:
        import google.generativeai as genai

        gemini_api_key = os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=gemini_api_key)

        primary_model_name = os.environ.get("GEMINI_MODEL_PRIMARY", "gemini-2.5-pro")
        fallback_model_name = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash")

        model = genai.GenerativeModel(
            model_name=primary_model_name,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=800,
                temperature=0.1,
            ),
        )

        system_prompt = (
            "Kamu adalah sistem otomatis JSEP milik Dinas Perhubungan DKI Jakarta. "
            "Tugas kamu adalah membuat berita acara pelanggaran lalu lintas yang formal, "
            "ringkas, dan mengacu pada dasar hukum yang tepat. "
            "Output HANYA teks berita acara, tanpa komentar tambahan, tanpa markdown."
        )
        user_prompt = f"""
Konteks Hukum:
{chr(10).join(legal_context)}

Data Pelanggaran:
- Nomor Polisi    : {violation.get('plate', '')}
- Jenis Pelanggaran: {violation.get('violation_type', '')}
- Lokasi/Zona     : {violation.get('zone_name', '')}
- Durasi          : {violation.get('duration_s', '')} detik
- Waktu Kejadian  : {violation.get('timestamp', '')}
- Kamera ID       : {violation.get('camera_id', '')}
- Petugas Verifikasi: {violation.get('officer_id', '')}
- Confidence Score: {float(violation.get('confidence', 0.0)):.3f}

Buat berita acara resmi sesuai format standar DISHUB DKI Jakarta.
"""
        try:
            response = model.generate_content([system_prompt, user_prompt])
        except Exception as e:
            print(f"Primary model {primary_model_name} failed: {e}. Falling back to {fallback_model_name}")
            fallback_model = genai.GenerativeModel(
                model_name=fallback_model_name,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=800,
                    temperature=0.1,
                ),
            )
            response = fallback_model.generate_content([system_prompt, user_prompt])
            
        return response.text.strip()
    except Exception:
        return _static_ba_fallback(violation)


def _static_ba_fallback(v: dict) -> str:
    from jinja2 import Template
    
    template_path = PROJECT_ROOT / "templates" / "berita_acara_static.j2"
    if not template_path.exists():
        template_path = Path("templates/berita_acara_static.j2")
        
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.render(**v)
