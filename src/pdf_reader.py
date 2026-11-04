"""
pdf_reader.py - Step 1: turn a PDF into text, page by page.
Reading a 280-page PDF takes a while, so we save (cache) the result and reuse it next time.
"""
import json
import hashlib
from pathlib import Path
import pymupdf          # the PDF library (installed as 'pymupdf')
from . import config


def _cache_file(pdf_path: Path) -> Path:
    stat = pdf_path.stat()
    key = hashlib.md5(f"{pdf_path.name}-{stat.st_size}-{int(stat.st_mtime)}".encode()).hexdigest()[:10]
    folder = config.CACHE_DIR / "pages"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{pdf_path.stem}_{key}.json"


def load_pages(pdf_path, use_cache=True) -> dict:
    """Return {page_number: text}. Page numbers start at 1 (the PDF's own page order)."""
    pdf_path = Path(pdf_path)
    cache = _cache_file(pdf_path)
    if use_cache and cache.exists():
        return {int(k): v for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    pages = {}
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            text = text.replace("\xa0", " ").replace("\u200b", "")
            text = "".join(ch for ch in text if ch == "\n" or ch >= " ")   # drop control characters
            pages[i] = text
    cache.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def is_probably_scanned(pages: dict) -> bool:
    """If the average page has almost no text, the PDF is probably a scan (needs OCR - not supported)."""
    if not pages:
        return True
    avg = sum(len(t) for t in pages.values()) / len(pages)
    return avg < 200
