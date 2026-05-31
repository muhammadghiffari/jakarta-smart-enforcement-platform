#!/usr/bin/env python3
"""
scripts/pdf_to_rag.py
Extract text from legal PDF documents → rag_corpus/*.txt for ChromaDB indexing.

Usage:
  python scripts/pdf_to_rag.py --input path/to/pdfs/ --output rag_corpus/
  python scripts/pdf_to_rag.py --input single_file.pdf --output rag_corpus/

Handles: UU LLAJ 22/2009, Pergub 155/2018, Pergub 88/2019,
         PM Kemenhub 15/2019, PM Kemenhub 025, BA examples, penalty schedule.

Install: pip install pymupdf tqdm  (fitz = PyMuPDF)
"""

import argparse
import re
import sys
from pathlib import Path

def extract_pdf_text(pdf_path: Path) -> str:
    """Extract all text from PDF using PyMuPDF (best for Indonesian legal docs)."""
    try:
        import fitz  # pip install pymupdf
    except ImportError:
        print("ERROR: pip install pymupdf")
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        # Add page marker for chunk tracing
        pages.append(f"[Halaman {page_num + 1}]\n{text}")
    doc.close()
    return "\n\n".join(pages)


def clean_legal_text(text: str) -> str:
    """Clean common OCR artifacts in Indonesian legal documents."""
    # Fix common OCR errors in Indonesian legal PDFs
    replacements = {
        r'\bPasa1\b': 'Pasal',          # OCR '1' instead of 'l'
        r'\bpaaa1\b': 'pasal',
        r'\bUndang-Undang\b': 'Undang-Undang',
        r'(?<=[a-z])(?=[A-Z])': ' ',     # missing space between words
        r'\n{3,}': '\n\n',               # excessive blank lines
        r'[ \t]{2,}': ' ',              # multiple spaces
        r'\f': '\n\n--- HALAMAN BARU ---\n\n',  # form feed
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """
    Chunk text for ChromaDB indexing.
    chunk_size=512 chars, overlap=50 chars (PRD FR-REP-06 spec).
    Tries to break at sentence boundaries.
    """
    chunks = []
    # Try to split on paragraph/sentence boundaries first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Para itself might be longer than chunk_size
            if len(para) > chunk_size:
                # Force-split long paragraphs
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size])
                current_chunk = para[-(overlap):]
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if len(c.strip()) > 20]  # filter tiny chunks


# Map filename patterns to standardized output names and metadata.
DOCUMENT_MAP = {
    # UU LLAJ
    r'uu.*22.*2009|llaj.*22|22.*2009.*llaj': {
        'output': 'uu_llaj_22_2009_relevant.txt',
        'description': 'UU No. 22 Tahun 2009 tentang Lalu Lintas dan Angkutan Jalan',
        'key_articles': ['Pasal 106', 'Pasal 275', 'Pasal 284', 'Pasal 287', 'Pasal 288'],
    },
    # Pergub 155/2018 Ganjil-Genap
    r'pergub.*155.*2018|ganjil.?genap|155.*2018': {
        'output': 'pergub_dki_155_2018_ganjilgenap.txt',
        'description': 'Pergub DKI Jakarta No. 155 Tahun 2018 tentang Pembatasan Lalu Lintas Ganjil-Genap',
    },
    # Pergub 88/2019
    r'pergub.*88.*2019|88.*2019': {
        'output': 'pergub_dki_88_2019.txt',
        'description': 'Pergub DKI Jakarta No. 88 Tahun 2019',
    },
    # PM Kemenhub 15/2019 (halte)
    r'pm.*15.*2019|perhubungan.*15.*2019|halte|15.*2019': {
        'output': 'pm_perhubungan_15_2019_halte.txt',
        'description': 'PM Perhubungan No. 15 Tahun 2019 (ketentuan halte)',
    },
    # PM Kemenhub 025
    r'pm.*025|kemenhub.*025|025.*kemenhub': {
        'output': 'pm_kemenhub_025.txt',
        'description': 'PM Kemenhub No. 25 (ketentuan angkutan jalan)',
    },
    # Penalty schedule / Pergub 31/2017
    r'pergub.*31.*2017|denda|sanksi|penalty|2017.*pergub.*31|0031031': {
        'output': 'daftar_sanksi_pelanggaran.txt',
        'description': 'Daftar Sanksi Pelanggaran Lalu Lintas — Pergub DKI Jakarta',
    },
    # Optional BA examples. The current source set keeps BA filenames from source stems.
    r'ba.*example|contoh.*ba|berita.*acara.*contoh|ba_\d+': {
        'output': None,
        'description': 'Contoh Berita Acara Pelanggaran',
    },
    # Optional BA format. Not present in the current corpus.
    r'ba.*format|format.*ba|format.*berita.*acara': {
        'output': None,
        'description': 'Format Berita Acara E-TLE DISHUB DKI Jakarta',
    },
}


def match_document(filename: str) -> dict | None:
    """Match PDF filename to document metadata."""
    fname_lower = filename.lower().replace('-', '_').replace(' ', '_')
    for pattern, meta in DOCUMENT_MAP.items():
        if re.search(pattern, fname_lower):
            return meta
    return None


def process_single_pdf(pdf_path: Path, output_dir: Path,
                        ba_counter: list, verbose: bool = True) -> str | None:
    """Process one PDF → text file in output_dir."""
    meta = match_document(pdf_path.name)

    if meta is None:
        # Unknown document — use filename as output name
        out_name = pdf_path.stem.lower().replace(' ', '_') + '.txt'
        description = f'Dokumen hukum: {pdf_path.name}'
    elif meta.get('output') is None:
        # Keep source-derived BA filenames so docs, corpus, and PRD stay aligned.
        ba_counter[0] += 1
        out_name = pdf_path.stem.lower().replace(' ', '_') + '.txt'
        description = meta['description'] + f' #{ba_counter[0]}'
    else:
        out_name = meta['output']
        description = meta['description']

    out_path = output_dir / out_name

    if verbose:
        print(f"  Processing: {pdf_path.name}")
        print(f"  → Output  : {out_name}")

    raw_text = extract_pdf_text(pdf_path)
    clean = clean_legal_text(raw_text)

    # Add header metadata for ChromaDB source tracking
    header = f"""# {description}
# Sumber: {pdf_path.name}
# Diekstrak: {Path(__file__).name}
# Untuk: JSEP DISHUB DKI Jakarta — RAG NarrativeAgent (FR-REP-06)
# ---

"""
    final_text = header + clean

    out_path.write_text(final_text, encoding='utf-8')

    chunks = chunk_text(clean)
    if verbose:
        print(f"  ✓ {len(clean):,} chars → {len(chunks)} chunks (target ~512 chars each)")

    return str(out_path)


def verify_corpus(output_dir: Path):
    """Check which required files are present / missing."""
    required = {
        'uu_llaj_22_2009_relevant.txt':   'UU LLAJ 22/2009',
        'pergub_dki_155_2018_ganjilgenap.txt': 'Pergub 155/2018 Ganjil-Genap',
        'pergub_dki_88_2019.txt':          'Pergub 88/2019',
        'pm_perhubungan_15_2019_halte.txt':'PM Kemenhub 15/2019',
        'pm_kemenhub_025.txt':            'PM Kemenhub 025',
        'daftar_sanksi_pelanggaran.txt':   'Daftar Sanksi',
    }
    print("\n=== RAG Corpus Status ===")
    all_ok = True
    for fname, desc in required.items():
        path = output_dir / fname
        if path.exists():
            size = path.stat().st_size
            chunks = len(chunk_text(path.read_text(encoding='utf-8')))
            print(f"  ✓ {fname:45s} ({size:>7,} bytes, ~{chunks} chunks)")
        else:
            print(f"  ✗ MISSING: {fname:40s} ({desc})")
            all_ok = False

    # Count BA-style outputs produced from the available source PDFs
    ba_files = [
        f for f in output_dir.glob('*.txt')
        if f.name.startswith(('ba_', 'berita_acara_', 'c-14.-'))
    ]
    print(f"  {'✓' if len(ba_files) >= 8 else '⚠'} BA examples/templates: {len(ba_files)} files")

    format_etle = output_dir / 'format_etle_berita_acara.txt'
    if format_etle.exists():
        print(f"  ✓ format_etle_berita_acara.txt                ({format_etle.stat().st_size:>7,} bytes, ~{len(chunk_text(format_etle.read_text(encoding='utf-8')))} chunks)")
    else:
        print("  ○ Optional: format_etle_berita_acara.txt (not present in current source set)")

    total_files = len(list(output_dir.glob('*.txt')))
    total_size = sum(f.stat().st_size for f in output_dir.glob('*.txt'))
    print(f"\n  Total: {total_files} files, {total_size:,} bytes")
    print(f"  Status: {'✓ COMPLETE — ready for ChromaDB indexing' if all_ok else '⚠ INCOMPLETE — missing files above'}")
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description='Extract legal PDFs to rag_corpus/ for JSEP NarrativeAgent'
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Input PDF file or directory containing PDFs')
    parser.add_argument('--output', '-o', default='rag_corpus',
                        help='Output directory for .txt files (default: rag_corpus/)')
    parser.add_argument('--verify', action='store_true',
                        help='Verify corpus completeness after extraction')
    parser.add_argument('--quiet', '-q', action='store_true')
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect PDFs
    if input_path.is_dir():
        pdf_files = sorted(input_path.glob('**/*.pdf'))
    elif input_path.suffix.lower() == '.pdf':
        pdf_files = [input_path]
    else:
        print(f"ERROR: {input_path} is not a PDF or directory")
        sys.exit(1)

    if not pdf_files:
        print(f"No PDFs found in {input_path}")
        sys.exit(1)

    print(f"\nJSEP PDF → RAG Corpus Extractor")
    print(f"Input : {input_path} ({len(pdf_files)} PDFs)")
    print(f"Output: {output_dir}/\n")

    ba_counter = [0]  # mutable counter for BA examples
    processed = []

    for pdf in pdf_files:
        try:
            out = process_single_pdf(pdf, output_dir, ba_counter, verbose=not args.quiet)
            if out:
                processed.append(out)
        except Exception as e:
            print(f"  ✗ ERROR processing {pdf.name}: {e}")

    print(f"\nProcessed {len(processed)}/{len(pdf_files)} files successfully.")

    if args.verify or True:  # always verify
        verify_corpus(output_dir)

    print(f"\nNext step — index into ChromaDB:")
    print(f"  python -c \"from services.narrative_agent.rag_agent import index_legal_corpus; index_legal_corpus('{output_dir}')\"")


if __name__ == '__main__':
    main()
