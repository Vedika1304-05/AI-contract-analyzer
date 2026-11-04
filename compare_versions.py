"""
compare_versions.py - compare ALL prompt versions / models / engines you have scored so far.
   python compare_versions.py                       (everything)
   python compare_versions.py --contract train1_NITI   (one contract only)

Reads outputs/experiment_log.csv and outputs/experiment_clause_log.csv (written by run_evaluation.py).
Saves outputs/version_comparison.csv and outputs/clause_matrix.csv for your report.
"""
import argparse
import pandas as pd
from src import config

parser = argparse.ArgumentParser()
parser.add_argument("--contract", default=None, help="only this contract (file name without .pdf)")
args = parser.parse_args()

log_path = config.OUTPUT_DIR / "experiment_log.csv"
clause_path = config.OUTPUT_DIR / "experiment_clause_log.csv"
if not log_path.exists():
    raise SystemExit("No experiment log yet. Run run_evaluation.py first.")

# (pandas reads the text "n/a" as a missing value, so we replace missing labels with "none")
LABELS = {"provider": "none", "model": "none", "prompt_version": "none"}
log = pd.read_csv(log_path).fillna(LABELS).drop_duplicates(subset=["result_file", "key_file"], keep="last")
cl = pd.read_csv(clause_path).fillna(LABELS).drop_duplicates(subset=["result_file", "key_file", "clause"], keep="last")
if args.contract:
    log, cl = log[log["contract"] == args.contract], cl[cl["contract"] == args.contract]

log["setup"] = log["engine"] + " | " + log["prompt_version"].astype(str) + " | " + log["model"].astype(str)
cols = ["correct", "incorrect", "missed", "invented", "unverified_quotes", "recall", "precision"]
summary = (log.groupby(["contract", "setup"])[cols].mean().round(2)
              .join(log.groupby(["contract", "setup"]).size().rename("runs")))
print("\n=== Average scores per contract and setup (sorted by recall) ===")
print(summary.sort_values(["contract", "recall"], ascending=[True, False]).to_string())
summary.to_csv(config.OUTPUT_DIR / "version_comparison.csv")

cl["setup"] = cl["engine"] + " | " + cl["prompt_version"].astype(str) + " | " + cl["model"].astype(str)
matrix = cl.pivot_table(index=["contract", "clause"], columns="setup", values="outcome",
                        aggfunc=lambda x: x.iloc[-1])
print("\n=== Outcome per clause (last run of each setup) ===")
print(matrix.to_string())
matrix.to_csv(config.OUTPUT_DIR / "clause_matrix.csv")
print("\nSaved: outputs/version_comparison.csv and outputs/clause_matrix.csv")
