"""
run_evaluation.py - score the tool against your answer key AND keep a permanent record.

Example:
  python run_evaluation.py --key benchmark/answer_key_train1.csv --results outputs/train1__llm__extract_v2__*__run1.json
You can list several files, and wildcards (*) work even on Windows.

Every scored file is APPENDED to:
  outputs/experiment_log.csv          one row per result file (scores)
  outputs/experiment_clause_log.csv   one row per clause per result file (what was right/wrong)
Nothing is overwritten, so you can compare all prompt versions later with compare_versions.py
"""
import argparse
import glob
from datetime import datetime
from pathlib import Path
import pandas as pd
from src import config, pipeline, evaluate

parser = argparse.ArgumentParser()
parser.add_argument("--key", required=True, help="answer key CSV")
parser.add_argument("--results", required=True, nargs="+", help="result JSON file(s); wildcards allowed")
args = parser.parse_args()

files = sorted({f for pattern in args.results for f in glob.glob(pattern)})
if not files:
    raise SystemExit("No result files matched. Check the path (look inside the outputs folder).")

key = evaluate.load_key(args.key)
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
run_rows, clause_rows, tables = [], [], []

for path in files:
    analysis = pipeline.load_analysis(path)
    df = evaluate.evaluate(analysis["results"], key)
    summ = evaluate.summarise(df, analysis["results"])
    print("=" * 80)
    print(path)
    print(df[["clause", "outcome", "tool_check", "key_value", "tool_value", "key_cap", "tool_cap"]].to_string(index=False))
    print("Summary:", summ)
    meta = {"timestamp": now, "contract": analysis["contract"], "engine": analysis["engine"],
            "provider": analysis.get("provider"), "model": analysis.get("model"),
            "prompt_version": analysis.get("prompt_version"), "run_id": analysis["run_id"],
            "key_file": Path(args.key).name, "result_file": Path(path).name}
    run_rows.append({**meta, **summ})
    for _, r in df.iterrows():
        clause_rows.append({**meta, "clause": r["clause"], "outcome": r["outcome"], "tool_check": r["tool_check"],
                            "key_value": r["key_value"], "tool_value": r["tool_value"],
                            "key_cap": r["key_cap"], "tool_cap": r["tool_cap"], "reason": r["reason"]})
    d = df.copy()
    d.insert(0, "result_file", Path(path).name)
    tables.append(d)


def append_csv(path: Path, rows: list):
    new = pd.DataFrame(rows)
    if path.exists():
        new = pd.concat([pd.read_csv(path), new], ignore_index=True)
    new.to_csv(path, index=False)


append_csv(config.OUTPUT_DIR / "experiment_log.csv", run_rows)
append_csv(config.OUTPUT_DIR / "experiment_clause_log.csv", clause_rows)
detail = config.OUTPUT_DIR / f"evaluation_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
pd.concat(tables).to_csv(detail, index=False)
print(f"\nLogged to outputs/experiment_log.csv and outputs/experiment_clause_log.csv")
print(f"Detail table for your discrepancy report: {detail}")

if len(files) > 1:
    full = pd.concat(tables)
    same = full.groupby("clause").apply(lambda g: g["tool_value"].nunique(dropna=False) == 1)
    print(f"Consistency across these files: {int(same.sum())} of {len(same)} clauses gave the same value every time.")
