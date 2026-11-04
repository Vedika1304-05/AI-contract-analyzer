"""
evaluate.py - Stage 5: compare the tool's output with YOUR manual answer key.

Answer key CSV columns:
 clause_type, present (yes/no), numeric_value, cap_percent, unit, clause_number, page, quote, notes
(clause_type must be one of: payment_terms, retention, advance, liquidated_damages, escalation, performance_security)

Outcome for each clause type:
 correct         - clause present in key, tool found it with the same value
 incorrect       - tool found it but the value/cap is wrong
 missed          - clause present in key, tool did not find it
 invented        - clause ABSENT in key but the tool 'found' it (a false positive / hallucination)
 correct_absent  - clause absent in key and the tool correctly said not found
"""
import pandas as pd
from .utils import to_per_week

TOL = 0.01


def load_key(path) -> dict:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    key = {}
    for _, row in df.iterrows():
        key[str(row["clause_type"]).strip()] = row
    return key


def _num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None


def _same(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= TOL


def evaluate(results: dict, key: dict) -> pd.DataFrame:
    rows = []
    for clause, krow in key.items():
        res = results.get(clause)
        if res is None:
            continue
        present = str(krow["present"]).strip().lower() in ("yes", "y", "true", "1")
        k_val, k_cap = _num(krow.get("numeric_value")), _num(krow.get("cap_percent"))
        t_val, t_cap = res.numeric_value, res.cap_percent
        if clause == "liquidated_damages":
            k_val = to_per_week(k_val, krow.get("unit"))
            t_val = to_per_week(t_val, res.unit)

        if present:
            if not res.found:
                outcome, why = "missed", "Tool did not find a clause that is in the key."
            else:
                ok_val = _same(k_val, t_val)
                ok_cap = True if k_cap is None else _same(k_cap, t_cap)
                if ok_val and ok_cap:
                    outcome, why = "correct", ""
                else:
                    outcome = "incorrect"
                    why = f"Key value={k_val}, cap={k_cap}; tool value={t_val}, cap={t_cap}."
        else:
            if res.found:
                outcome, why = "invented", "Key says the clause is absent but the tool reported one."
            else:
                outcome, why = "correct_absent", ""
        rows.append({"clause": clause, "outcome": outcome, "reason": why, "tool_check": res.verification,
                     "key_value": k_val, "tool_value": t_val, "key_cap": k_cap, "tool_cap": t_cap,
                     "tool_page": res.page, "key_page": krow.get("page")})
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame, results: dict) -> dict:
    n = lambda o: int((df["outcome"] == o).sum())
    present = n("correct") + n("incorrect") + n("missed")
    tool_found = sum(1 for r in results.values() if r.found)
    correct = n("correct")
    return {"clauses_in_key_present": present, "correct": correct, "incorrect": n("incorrect"),
            "missed": n("missed"), "invented": n("invented"), "correct_absent": n("correct_absent"),
            "recall": round(correct / present, 3) if present else None,
            "precision": round(correct / tool_found, 3) if tool_found else None,
            "unverified_quotes": sum(1 for r in results.values() if r.found and r.verification == "unverified")}
