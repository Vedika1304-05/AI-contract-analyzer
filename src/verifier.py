"""
verifier.py - Step 4: the anti-hallucination check.
The AI must give an exact quote. We check that this quote REALLY exists in the contract.
  verified          -> quote found exactly on the stated page
  page_corrected    -> quote found exactly, but on a different page (we fix the page number)
  partially_matched -> most of the quote matches (small copy errors) - check by eye
  unverified        -> quote NOT found anywhere: possible invented text. Treat as untrusted!
  quote_too_short   -> quote has fewer than 15 letters/digits, so it cannot prove anything. Treat as untrusted!
"""
from .utils import squash, numbers_in_text


def _ngrams(s: str, n: int = 12):
    return {s[i:i + n] for i in range(max(len(s) - n + 1, 1))}


def _overlap(quote_sq: str, page_sq: str) -> float:
    q = _ngrams(quote_sq)
    if not q:
        return 0.0
    return len(q & _ngrams(page_sq)) / len(q)


def verify(result, pages: dict):
    if not result.quote.strip():
        result.verification = "no_quote" if result.found else "n/a"
        return result

    q = squash(result.quote)
    if len(q) < 15:      # a tiny "quote" like "5%" would match almost anywhere, so it proves nothing
        result.verification = "quote_too_short"
        return result
    page_sq = {p: squash(t) for p, t in pages.items()}

    if result.page in page_sq and q in page_sq[result.page]:
        result.verification = "verified"
    else:
        hits = [p for p, t in page_sq.items() if q in t]
        if hits:
            result.verification = "page_corrected"
            result.notes = (result.notes + f" [page corrected from {result.page} to {hits[0]}]").strip()
            result.page = hits[0]
        else:
            best = 0.0
            candidates = [p for p in (result.page, (result.page or 0) - 1, (result.page or 0) + 1) if p in page_sq]
            for p in candidates:
                best = max(best, _overlap(q, page_sq[p]))
            result.verification = "partially_matched" if best >= 0.85 else "unverified"

    # does the reported number actually appear inside the quote?
    if result.numeric_value is not None:
        nums = numbers_in_text(result.quote)
        result.value_in_quote = any(abs(n - result.numeric_value) < 1e-6 for n in nums)
    return result
