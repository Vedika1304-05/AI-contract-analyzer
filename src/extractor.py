"""
extractor.py - Step 3: ask the AI to extract one clause type from the best chunks.
The AI must answer in JSON, which we check with pydantic (a data-checking library).
"""
import json
import re
from typing import Optional
from pydantic import BaseModel, field_validator
from . import config
from .llm import ask_llm

try:
    from .hints import HINTS          # clause-specific reading guidance (used by prompts v3-v5)
except ImportError:
    HINTS = {}


class ClauseResult(BaseModel):
    """The shape of one extracted clause. Every result in the tool has these fields."""
    clause: str
    found: bool = False
    explicitly_excluded: bool = False
    value_text: str = ""
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    cap_percent: Optional[float] = None
    day_type: Optional[str] = None
    clause_number: Optional[str] = None
    page: Optional[int] = None
    quote: str = ""
    confidence: str = "low"
    notes: str = ""
    reasoning: str = ""                    # the AI's short evidence analysis (prompts v3-v5)
    verification: str = "not_checked"      # filled later by verifier.py
    value_in_quote: Optional[bool] = None  # filled later by verifier.py
    engine: str = ""
    error: str = ""

    @field_validator("numeric_value", "cap_percent", mode="before")
    @classmethod
    def _to_float(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        m = re.search(r"\d+(?:\.\d+)?", str(v))
        return float(m.group()) if m else None

    @field_validator("page", mode="before")
    @classmethod
    def _to_int(cls, v):
        if v is None or v == "":
            return None
        m = re.search(r"\d+", str(v))
        return int(m.group()) if m else None

    @field_validator("clause_number", "unit", "day_type", mode="before")
    @classmethod
    def _to_str(cls, v):
        return None if v in (None, "") else str(v)


def load_prompt_template() -> str:
    path = config.PROMPT_DIR / f"{config.PROMPT_VERSION}.txt"
    return path.read_text(encoding="utf-8")


def build_prompt(clause_key: str, chunks: list) -> str:
    info = config.CLAUSES[clause_key]
    excerpts = "\n\n".join(f"--- EXCERPT (PAGE {c.page}) ---\n{c.text}" for c in chunks)
    return (load_prompt_template()
            .replace("<<CLAUSE_LABEL>>", info["label"])
            .replace("<<CLAUSE_DEFINITION>>", info["definition"])
            .replace("<<CLAUSE_HINTS>>", HINTS.get(clause_key, ""))
            .replace("<<EXCERPTS>>", excerpts))


def parse_json(text: str) -> dict:
    """Pull the JSON object out of the AI's reply, even if it added ```json fences or extra words."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in the AI reply")
    data = json.loads(text[start:end + 1])
    if isinstance(data, list):
        data = data[0]
    return data


def extract_clause(clause_key: str, chunks: list, run_id: int = 1) -> ClauseResult:
    """One clause type -> one ClauseResult. Never crashes: errors are recorded in the result."""
    engine = f"llm:{config.PROVIDER}:{config.PROMPT_VERSION}"
    if not chunks:
        return ClauseResult(clause=clause_key, found=False, engine=engine,
                            notes="No text matching this clause's keywords was found "
                                  "(possible retrieval miss: check wording/keywords).")
    prompt = build_prompt(clause_key, chunks)
    try:
        raw = ask_llm(prompt, run_id=run_id)
        data = parse_json(raw)
        if "evidence_analysis" in data:
            data["reasoning"] = data.pop("evidence_analysis")
        data = {k: v for k, v in data.items() if k in ClauseResult.model_fields}
        data.pop("clause", None)
        return ClauseResult(clause=clause_key, engine=engine, **data)
    except Exception as e:
        return ClauseResult(clause=clause_key, found=False, engine=engine, error=str(e),
                            notes="Extraction failed - see error.")
