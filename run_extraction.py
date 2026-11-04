"""
run_extraction.py - run the tool on ONE contract from the command line.

Examples (from the project folder, with the virtual environment active):
  python run_extraction.py --pdf data/train/train1.pdf --engine baseline
  python run_extraction.py --pdf data/train/train1.pdf --engine llm --prompt extract_v1 --run 1
"""
import argparse
import pandas as pd
from src import config, pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--pdf", required=True, help="path to the contract PDF")
parser.add_argument("--engine", default="llm", choices=["llm", "baseline"])
parser.add_argument("--run", type=int, default=1, help="run number (use 1, 2, 3 for repeat runs)")
parser.add_argument("--prompt", default=None,
                    help="prompt version, e.g. extract_v2 (overrides .env and any terminal setting)")
parser.add_argument("--top-k", type=int, default=None, help="chunks sent to the AI per clause")
args = parser.parse_args()

if args.prompt:
    config.PROMPT_VERSION = args.prompt

if args.engine == "llm":
    prompt_file = config.PROMPT_DIR / f"{config.PROMPT_VERSION}.txt"
    if not prompt_file.exists():
        available = sorted(p.stem for p in config.PROMPT_DIR.glob("extract_v*.txt"))
        raise SystemExit(f"Prompt file not found: {prompt_file.name}. Available: {available}")
    model = getattr(pipeline, "_model_name", lambda: "?")()
    print(f"Engine: llm | provider: {config.PROVIDER} | model: {model} | "
          f"prompt version: {config.PROMPT_VERSION} | run: {args.run}")
else:
    print("Engine: baseline (rules only, no AI)")


def show_progress(i, total, clause):
    print(f"  [{i}/{total}] extracting {clause} ...")


print(f"Reading {args.pdf}")
analysis = pipeline.analyse(args.pdf, engine=args.engine, run_id=args.run,
                            top_k=args.top_k, progress=show_progress)
table = pipeline.results_table(analysis)

path = pipeline.analysis_path(analysis)
table.to_csv(path.with_suffix(".csv"), index=False)       # saved BEFORE printing


def clean(x):
    return "" if pd.isna(x) else x


print()
for _, r in table.iterrows():
    print(f"{r['Clause']:<22} found={str(r['Found']):<5} value={str(clean(r['Value'])):<6} "
          f"unit={str(clean(r['Unit'])):<20} page={str(clean(r['Page'])):<5} check={r['Check']}")
print(f"\nSaved: {path}\n       {path.with_suffix('.csv')}")
print("Reminder: every 'found' value must still be checked by a human against the original contract.")