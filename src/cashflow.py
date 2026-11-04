"""
cashflow.py - Step 6: turn contract terms into monthly cash flow, peak funding and interest.
It follows EXACTLY the same rules as your Excel benchmark. If the two disagree, one of them has a bug.

Rules (write the same ones in your Excel sheet):
 1. Month 0: the mobilisation advance (advance% x contract value) is received.
 2. Months 1..N: billing = contract value x S-curve share of that month.
 3. Retention held = retention% x billing, but total retention never exceeds the cap (if any).
 4. Advance recovered = recovery% x billing, until the advance is fully recovered.
 5. Net bill = billing - retention - advance recovered.
 6. Cash is RECEIVED 'payment delay' months after billing (whole months).
 7. Cost paid in the same month as billing = cost ratio x billing.
 8. All retention is released in month N + max(payment delay, defects liability months).
 9. Cumulative cash = running total of (advance + receipts + retention released - cost paid).
10. Overdraft = max(0, -cumulative cash). Interest each month = overdraft x annual rate / 12 (simple, not compounded).
Peak funding = the largest overdraft. Amounts are in whatever unit you use for contract value (e.g. Rs lakh).
"""
import numpy as np
import pandas as pd

DEFAULT_S_CURVE_10 = [5, 8, 10, 12, 14, 14, 12, 10, 9, 6]


def default_s_curve(n: int):
    if n == 10:
        return list(DEFAULT_S_CURVE_10)
    x = np.linspace(0, 1, n)
    w = np.sin(np.pi * x) + 0.15
    return list(w / w.sum() * 100)


def run_cashflow(contract_value, duration, s_curve=None, retention_pct=0.0, retention_cap_pct=None,
                 payment_delay_months=0, advance_pct=0.0, advance_recovery_pct=None,
                 cost_ratio=0.90, overdraft_rate=0.11, dlp_months=12):
    n = int(duration)
    delay = int(round(payment_delay_months))
    s = np.array(s_curve if s_curve is not None else default_s_curve(n), dtype=float)
    if len(s) != n:
        raise ValueError(f"S-curve has {len(s)} values but duration is {n} months")
    s = s / s.sum()
    adv_rec_pct = advance_pct if advance_recovery_pct is None else advance_recovery_pct

    release_month = n + max(delay, int(dlp_months))
    H = release_month
    z = lambda: np.zeros(H + 1)
    billing, ret, adv_rec, net_bill, received, cost = z(), z(), z(), z(), z(), z()
    adv_in, release = z(), z()

    cap_amt = retention_cap_pct / 100 * contract_value if retention_cap_pct else float("inf")
    adv_total = advance_pct / 100 * contract_value
    adv_left, cum_ret = adv_total, 0.0
    adv_in[0] = adv_total

    for t in range(1, n + 1):
        b = contract_value * s[t - 1]
        billing[t] = b
        r = max(min(retention_pct / 100 * b, cap_amt - cum_ret), 0.0)
        cum_ret += r
        ret[t] = r
        a = min(adv_rec_pct / 100 * b, adv_left)
        adv_left -= a
        adv_rec[t] = a
        net_bill[t] = b - r - a
        received[t + delay] += net_bill[t]
        cost[t] = cost_ratio * b
    release[release_month] = cum_ret

    net_cash = adv_in + received + release - cost
    cum = np.cumsum(net_cash)
    overdraft = np.maximum(-cum, 0)
    interest = overdraft * overdraft_rate / 12

    df = pd.DataFrame({
        "Month": range(H + 1), "Billing": billing, "Retention held": ret, "Advance recovered": adv_rec,
        "Net bill": net_bill, "Advance received": adv_in, "Cash received": received,
        "Retention released": release, "Cost paid": cost, "Net cash": net_cash,
        "Cumulative cash": cum, "Overdraft": overdraft, "Interest": interest}).round(4)
    summary = {
        "peak_funding": float(overdraft.max()),
        "peak_month": int(overdraft.argmax()) if overdraft.max() > 0 else None,
        "total_interest": float(interest.sum()),
        "max_retention_locked": float(cum_ret),
        "final_cash": float(cum[-1]),
        "advance_unrecovered": float(adv_left),
    }
    return df, summary


def sensitivity_table(base_params: dict, delays=(1, 2, 3), retentions=(0, 5, 10)):
    """Peak funding and interest for different payment delays and retention percentages."""
    rows = []
    for d in delays:
        for r in retentions:
            p = dict(base_params, payment_delay_months=d, retention_pct=r)
            _, s = run_cashflow(**p)
            rows.append({"Payment delay (months)": d, "Retention %": r,
                         "Peak funding": round(s["peak_funding"], 2),
                         "Interest": round(s["total_interest"], 2)})
    return pd.DataFrame(rows)
