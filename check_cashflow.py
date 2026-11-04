"""
check_cashflow.py - prints the cash flow for the benchmark case so you can compare it
with YOUR Excel sheet, month by month. Build the Excel FIRST, then run this.
   python check_cashflow.py
"""
from src.cashflow import run_cashflow

df, s = run_cashflow(contract_value=1000, duration=10, retention_pct=5, payment_delay_months=2,
                     advance_pct=10, cost_ratio=0.90, overdraft_rate=0.11, dlp_months=0)
print(df[["Month", "Billing", "Retention held", "Advance recovered", "Net bill", "Cash received",
          "Cost paid", "Net cash", "Cumulative cash", "Overdraft", "Interest"]].to_string(index=False))
print("\nSummary:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()})
print("\nSelf-check: final cash should equal profit = 1000 x (1 - 0.90) = 100 ->",
      "PASS" if abs(s["final_cash"] - 100) < 1e-6 else "FAIL")
