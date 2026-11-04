"""
pipeline.py - joins all steps together:
PDF -> pages -> chunks -> best chunks per clause -> extraction (AI or baseline) -> quote check -> saved JSON.
"""
import json
from pathlib import Path
from . import config, pdf_reader, retrieval, extractor, baseline, verifier


def analyse(pdf_path, engine="llm", run_id=1, top_k=None, save=True, progress=None):
    """engine = 'llm' (uses your AI provider) or 'baseline' (rules only, no AI)."""
    pdf_path = Path(pdf_path)
    pages = pdf_reader.load_pages(pdf_path)
    if pdf_reader.is_probably_scanned(pages):
        raise ValueError(f"{pdf_path.name} looks like a scanned PDF (almost no text). "
                         "This tool needs a text-based PDF. Choose another file.")
    chunks = retrieval.build_chunks(pages)

    results = {}
    for i, clause_key in enumerate(config.CLAUSES, start=1):
        if progress:
            progress(i, len(config.CLAUSES), clause_key)
        top = retrieval.top_chunks(chunks, clause_key, top_k)
        if engine == "baseline":
            res = baseline.extract(clause_key, top)
        else:
            res = extractor.extract_clause(clause_key, top, run_id=run_id)
        results[clause_key] = verifier.verify(res, pages)

    analysis = {"contract": pdf_path.stem, "pdf": str(pdf_path), "n_pages": len(pages),
                "engine": engine, "run_id": run_id,
                "prompt_version": config.PROMPT_VERSION if engine == "llm" else "n/a",
                "provider": config.PROVIDER if engine == "llm" else "n/a",
                "model": _model_name() if engine == "llm" else "n/a",
                "results": results}
    if save:
        save_analysis(analysis)
    return analysis


def _model_name() -> str:
    return {"gemini": config.GEMINI_MODEL, "anthropic": config.ANTHROPIC_MODEL,
            "openai": config.OPENAI_MODEL}.get(config.PROVIDER, "manual")


def _safe(text) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9.-]+", "-", str(text)).strip("-")


def analysis_path(analysis) -> Path:
    """File name includes contract, engine, prompt version, model and run number,
    so results from different prompt versions / models never overwrite each other."""
    if analysis["engine"] == "llm":
        tag = f"{analysis['prompt_version']}__{_safe(analysis.get('model', 'unknown'))}"
    else:
        tag = "rules"
    return config.OUTPUT_DIR / f"{analysis['contract']}__{analysis['engine']}__{tag}__run{analysis['run_id']}.json"


def save_analysis(analysis) -> Path:
    out = dict(analysis)
    out["results"] = {k: v.model_dump() for k, v in analysis["results"].items()}
    path = analysis_path(analysis)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_analysis(path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["results"] = {k: extractor.ClauseResult(**v) for k, v in data["results"].items()}
    return data


def results_table(analysis):
    """A pandas table of the results (used by the screen and by the CSV export)."""
    import pandas as pd
    rows = []
    for k, r in analysis["results"].items():
        rows.append({"Clause": k, "Found": r.found, "Excluded": r.explicitly_excluded, "Value": r.numeric_value,
                     "Unit": r.unit, "Cap %": r.cap_percent, "Day type": r.day_type,
                     "Clause no.": r.clause_number, "Page": r.page, "Check": r.verification,
                     "Value in quote?": r.value_in_quote, "Confidence": r.confidence,
                     "Summary": r.value_text, "Quote": r.quote, "Notes": r.notes, "Error": r.error})
    df = pd.DataFrame(rows)
    df["Page"] = df["Page"].astype("Int64")
    return df


def cashflow_params_from_results(results, contract_value, duration, cost_ratio=0.90,
                                 overdraft_rate=0.11, dlp_months=12):
    """Turn extracted clauses into cash-flow inputs. Returns (params, list_of_assumptions)."""
    from .utils import days_to_calendar
    assumptions = []
    p = {"contract_value": contract_value, "duration": duration, "cost_ratio": cost_ratio,
         "overdraft_rate": overdraft_rate, "dlp_months": dlp_months}

    r = results["retention"]
    if r.found and r.numeric_value is not None:
        p["retention_pct"], p["retention_cap_pct"] = r.numeric_value, r.cap_percent
    else:
        p["retention_pct"], p["retention_cap_pct"] = 0.0, None
        assumptions.append("No retention found: assumed 0%.")

    r = results["payment_terms"]
    if r.found and r.numeric_value is not None:
        cal = days_to_calendar(r.numeric_value, r.day_type)
        p["payment_delay_months"] = round(cal / 30)
        assumptions.append(f"Payment delay {cal:.0f} days rounded to {round(cal / 30)} whole month(s).")
    else:
        p["payment_delay_months"] = 1
        assumptions.append("No payment period found: assumed 1 month.")

    r = results["advance"]
    if r.found and r.numeric_value is not None:
        p["advance_pct"] = r.numeric_value
    else:
        p["advance_pct"] = 0.0
        assumptions.append("No advance found: assumed 0%.")
    assumptions.append(f"Cost = {cost_ratio:.0%} of billing, paid in the month of billing; "
                       f"overdraft interest {overdraft_rate:.0%} per year; retention released after "
                       f"{dlp_months} months defects period.")
    return p, assumptions
