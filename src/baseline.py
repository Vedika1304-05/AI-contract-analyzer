"""
baseline.py - a NO-AI extractor made only of keyword + pattern rules (regular expressions).
It is deliberately simple. We run it on the same contracts as the AI so the report can say
"the AI beat the simple rules by X points" - a strong finding for the validation report.
"""
import re
from .extractor import ClauseResult
from . import config

PCT = r"(\d+(?:\.\d+)?)\s*(?:%|per\s?cent|percent)"
DAYS_RE = re.compile(r"within\s+(?:[a-z\-]+\s+)?\(?(\d{1,3})\)?\s*(?:\([a-z\- ]+\)\s*)?(working\s+|calendar\s+)?days", re.I)
PCT_RE = re.compile(PCT, re.I)
LD_RATE_RE = re.compile(PCT + r"[^.]{0,90}?\bper\s+(day|week|month)", re.I)
CAP_RE = re.compile(r"(?:maximum|not\s+exceed(?:ing)?|exceed|limit(?:ed)?\s+to|cap)[^.%]{0,90}?" + PCT, re.I)

CONTEXT_WORDS = {
    "retention": r"retention|security deposit|retained|withheld",
    "advance": r"advance",
    "performance_security": r"performance\s+(?:security|guarantee|bank)|bank guarantee",
    "payment_terms": r"payment|certificate|bill|invoice|honou?ring",
    "liquidated_damages": r"damages|compensation|delay",
}


def _flat(text):
    return re.sub(r"\s+", " ", text.replace("½", "0.5")).strip()


def _window(flat, start, end, pad=110):
    a, b = max(0, start - pad), min(len(flat), end + pad)
    a = flat.rfind(" ", 0, a + 1) + 1 if a > 0 else 0
    b = flat.find(" ", b) if flat.find(" ", b) != -1 else len(flat)
    return flat[a:b].strip()


def _near(flat, pos, pattern, dist=220):
    return any(abs(m.start() - pos) <= dist for m in re.finditer(pattern, flat, re.I))


def extract(clause_key, chunks) -> ClauseResult:
    res = ClauseResult(clause=clause_key, engine="baseline-regex", confidence="low")
    for ch in chunks:
        flat = _flat(ch.text)
        low = flat.lower()

        if clause_key == "escalation":
            if re.search(r"no\s+escalation|rates?\s+are\s+firm|firm\s+and\s+no", low):
                m = re.search(r"no\s+escalation|rates?\s+are\s+firm|firm\s+and\s+no", low)
                res.found, res.explicitly_excluded = False, True
                res.quote, res.page = _window(flat, m.start(), m.end()), ch.page
                res.value_text = "Contract says rates are firm / no escalation."
                return res
            m = re.search(r"price\s+(?:variation|adjustment|escalation)|escalation", low)
            if m:
                res.found, res.quote, res.page = True, _window(flat, m.start(), m.end()), ch.page
                res.value_text = "A price variation / adjustment / escalation clause appears to exist."
                return res
            continue

        if clause_key == "payment_terms":
            for m in DAYS_RE.finditer(flat):
                if _near(flat, m.start(), CONTEXT_WORDS["payment_terms"]):
                    res.found, res.numeric_value, res.unit = True, float(m.group(1)), "days"
                    res.day_type = (m.group(2) or "").strip().lower() or None
                    res.quote, res.page = _window(flat, m.start(), m.end()), ch.page
                    res.value_text = f"Payment within {m.group(1)} days."
                    return res
            continue

        if clause_key == "liquidated_damages":
            for m in LD_RATE_RE.finditer(flat):
                if _near(flat, m.start(), CONTEXT_WORDS["liquidated_damages"]):
                    res.found, res.numeric_value, res.unit = True, float(m.group(1)), f"% per {m.group(2).lower()}"
                    cap = CAP_RE.search(flat, m.start())
                    res.cap_percent = float(cap.group(1)) if cap else None
                    res.quote, res.page = _window(flat, m.start(), m.end()), ch.page
                    res.value_text = f"Delay damages {m.group(1)}% per {m.group(2).lower()}."
                    return res
            continue

        # retention, advance, performance_security: a percentage close to a context word
        ctx = CONTEXT_WORDS[clause_key]
        for m in PCT_RE.finditer(flat):
            if _near(flat, m.start(), ctx, 120):
                res.found, res.numeric_value, res.unit = True, float(m.group(1)), "%"
                if clause_key == "retention":
                    cap = CAP_RE.search(flat)
                    res.cap_percent = float(cap.group(1)) if cap else None
                res.quote, res.page = _window(flat, m.start(), m.end()), ch.page
                res.value_text = f"{m.group(1)}% found near the clause keywords (regex guess)."
                return res
    res.notes = "No matching pattern found by the rule-based baseline."
    return res
