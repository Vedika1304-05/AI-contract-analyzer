"""
retrieval.py - Step 2: find the few text pieces that matter.
We cut every page into small 'chunks', score each chunk against a clause type's keywords,
and keep only the best few. Only those chunks are sent to the AI (cheap, fast, less confusion).
"""
import re
from dataclasses import dataclass
from . import config


@dataclass
class Chunk:
    page: int
    start_line: int
    text: str
    score: float = 0.0


def build_chunks(pages: dict) -> list:
    """Cut each page into overlapping chunks of about CHUNK_CHARS characters (never across pages)."""
    chunks = []
    for page_no, text in pages.items():
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        i = 0
        while i < len(lines):
            size, j = 0, i
            while j < len(lines) and size + len(lines[j]) <= config.CHUNK_CHARS:
                size += len(lines[j]) + 1
                j += 1
            if j == i:          # a single very long line
                j = i + 1
            chunks.append(Chunk(page=page_no, start_line=i, text="\n".join(lines[i:j])))
            if j >= len(lines):
                break
            i = max(j - config.CHUNK_OVERLAP_LINES, i + 1)
    return chunks


_VALUE_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:%|per\s?cent|percent|days|day|weeks|week|months)", re.I)


def _looks_like_table_of_contents(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 4:
        return False
    toc_like = sum(1 for ln in lines if re.search(r"\.{4,}", ln) or re.search(r"\s\d{1,3}\s*$", ln))
    return toc_like / len(lines) > 0.45


def score_chunk(chunk: Chunk, clause_key: str) -> float:
    text = chunk.text.lower()
    keywords = config.CLAUSES[clause_key]["keywords"]
    score = 0.0
    for phrase, weight in keywords.items():
        hits = text.count(phrase)
        if hits:
            score += weight * min(hits, 3)           # cap so one repeated word cannot dominate
    if score == 0:
        return 0.0
    if _VALUE_PATTERN.search(chunk.text):
        score += 3                                    # chunks with an actual number are more useful
    if _looks_like_table_of_contents(chunk.text):
        score *= 0.2                                  # table-of-contents pages mention everything
    return score


def top_chunks(chunks: list, clause_key: str, k: int = None) -> list:
    """Return the k best chunks for a clause type (skipping chunks that mostly repeat one already chosen)."""
    k = k or config.TOP_K_CHUNKS
    for c in chunks:
        c.score = score_chunk(c, clause_key)
    ranked = sorted((c for c in chunks if c.score > 0), key=lambda c: c.score, reverse=True)
    chosen, used = [], set()
    for c in ranked:
        n_lines = len(c.text.splitlines())
        mine = {(c.page, c.start_line + n) for n in range(n_lines)}
        if len(mine & used) / max(len(mine), 1) >= 0.5:
            continue
        chosen.append(c)
        used |= mine
        if len(chosen) == k:
            break
    return chosen
