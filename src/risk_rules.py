"""
risk_rules.py - Step 5: turn extracted values into risk flags.
Thresholds are EDITABLE and each has a stated reason (you must justify them in the method note
and in the viva - they are judgement-based, not laws of nature).
"""
from .utils import to_per_week, days_to_calendar

THRESHOLDS = {
    "payment_days":     {"medium": 45, "high": 60,
                         "reason": "A longer wait for payment means the contractor must finance more work "
                                   "from his own pocket or an overdraft."},
    "retention_percent": {"medium": 5, "high": 10,
                          "reason": "Money held back from every bill is locked up for months and raises peak funding."},
    "ld_cap_percent":   {"medium": 5, "high": 10,
                         "reason": "The cap is the maximum penalty the contractor can lose for delay."},
    "ld_rate_per_week": {"medium": 0.5, "high": 1.0,
                         "reason": "A high weekly rate reaches the cap quickly if the project slips."},
    "perf_security_percent": {"medium": 5, "high": 10,
                              "reason": "A larger guarantee costs more in bank charges and uses up borrowing limits."},
    "escalation_min_months": 12,
}


def _level(value, rule):
    if value is None:
        return "info"
    if value > rule["high"]:
        return "high"
    if value > rule["medium"]:
        return "medium"
    return "low"


def assess(results: dict, duration_months=None) -> list:
    """results = {clause_key: ClauseResult}. Returns a list of flags (dicts)."""
    flags = []

    def add(clause, level, finding, reason):
        flags.append({"clause": clause, "level": level, "finding": finding, "reason": reason})

    r = results["payment_terms"]
    if r.found and r.numeric_value is not None:
        cal = days_to_calendar(r.numeric_value, r.day_type)
        t = THRESHOLDS["payment_days"]
        extra = f" (= about {cal:.0f} calendar days)" if r.day_type and r.day_type.startswith("work") else ""
        add("Payment terms", _level(cal, t), f"Payment due in {r.numeric_value:g} {r.day_type or ''} days{extra}.".replace("  ", " "), t["reason"])
    else:
        add("Payment terms", "info", "No payment period found - check manually.", "Cannot model the payment delay without it.")

    r = results["retention"]
    if r.found and r.numeric_value is not None:
        t = THRESHOLDS["retention_percent"]
        cap = f", capped at {r.cap_percent:g}% in total" if r.cap_percent else ""
        add("Retention", _level(r.numeric_value, t), f"{r.numeric_value:g}% held back from each bill{cap}.", t["reason"])
    else:
        add("Retention", "info", "No retention/security deposit percentage found.", "Check manually; value may sit in a schedule.")

    r = results["liquidated_damages"]
    if r.found:
        t1, t2 = THRESHOLDS["ld_cap_percent"], THRESHOLDS["ld_rate_per_week"]
        rate = to_per_week(r.numeric_value, r.unit)
        lvl_cap = _level(r.cap_percent, t1)
        lvl_rate = _level(rate, t2)
        order = {"info": 0, "low": 1, "medium": 2, "high": 3}
        lvl = max([lvl_cap, lvl_rate], key=lambda x: order[x])
        rate_txt = f"{rate:.2f}% per week" if rate is not None else "rate not found"
        cap_txt = f"cap {r.cap_percent:g}%" if r.cap_percent else "no cap found"
        add("Liquidated damages", lvl, f"Delay damages: {rate_txt}, {cap_txt}.", t1["reason"] + " " + t2["reason"])
    else:
        add("Liquidated damages", "info", "No delay-damages clause found.", "Check manually.")

    r = results["advance"]
    if r.found and r.numeric_value is not None:
        add("Mobilisation advance", "low", f"Advance of {r.numeric_value:g}% available. {r.notes}".strip(),
            "An advance helps early cash flow; check its recovery terms and any interest.")
    else:
        add("Mobilisation advance", "medium", "No mobilisation advance found.",
            "Without an advance the contractor must pre-finance start-up costs.")

    r = results["escalation"]
    long_job = duration_months is not None and duration_months > THRESHOLDS["escalation_min_months"]
    if r.found:
        add("Price escalation", "low", "A price variation/adjustment clause exists.", "Protects the contractor from price rises.")
    elif r.explicitly_excluded:
        add("Price escalation", "high" if long_job else "medium", "Rates are firm: escalation is explicitly excluded.",
            "The contractor carries all material and labour price risk.")
    else:
        add("Price escalation", "high" if long_job else "medium", "No escalation clause found.",
            "The contractor carries price risk (more serious on long contracts).")

    r = results["performance_security"]
    if r.found and r.numeric_value is not None:
        t = THRESHOLDS["perf_security_percent"]
        add("Performance security", _level(r.numeric_value, t), f"Performance security of {r.numeric_value:g}%.", t["reason"])
    else:
        add("Performance security", "info", "No performance security percentage found.", "Check manually.")
    return flags


def plain_summary(flags: list, cash_summary: dict = None) -> str:
    """A short plain-language summary for a non-technical reader (no AI needed)."""
    high = [f for f in flags if f["level"] == "high"]
    med = [f for f in flags if f["level"] == "medium"]
    lines = []
    if high:
        lines.append("HIGH risk: " + "; ".join(f["finding"] for f in high))
    if med:
        lines.append("MEDIUM risk: " + "; ".join(f["finding"] for f in med))
    if not high and not med:
        lines.append("No high or medium risks were flagged from the clauses that were found.")
    if cash_summary:
        lines.append(f"Under these terms the contractor's peak funding need is about {cash_summary['peak_funding']:.1f} "
                     f"(lakh), costing roughly {cash_summary['total_interest']:.1f} lakh in overdraft interest.")
    lines.append("Always verify each flagged clause against the original contract text before relying on this.")
    return "\n".join(lines)
