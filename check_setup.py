"""
check_setup.py - run this FIRST. It tells you if your setup is ready.
   python check_setup.py
"""
import importlib
from pathlib import Path

print("1) Checking libraries...")
for lib in ["pymupdf", "pydantic", "pandas", "numpy", "plotly", "streamlit", "dotenv"]:
    try:
        importlib.import_module(lib)
        print(f"   OK   {lib}")
    except ImportError:
        print(f"   MISSING {lib}  ->  run: pip install -r requirements.txt")

from src import config, pdf_reader

print("\n2) Checking contract PDFs in data/ ...")
pdfs = sorted((config.ROOT / "data").rglob("*.pdf"))
if not pdfs:
    print("   No PDFs found. Copy your contracts into data/train and data/test.")
for p in pdfs:
    pages = pdf_reader.load_pages(p)
    chars = sum(len(t) for t in pages.values())
    flag = "SCANNED? (replace this file)" if pdf_reader.is_probably_scanned(pages) else "text OK"
    print(f"   {p.relative_to(config.ROOT)}: {len(pages)} pages, {chars:,} characters -> {flag}")

print(f"\n3) AI provider = '{config.PROVIDER}'")
key = {"gemini": config.GEMINI_API_KEY, "anthropic": config.ANTHROPIC_API_KEY,
       "openai": config.OPENAI_API_KEY, "manual": "n/a"}.get(config.PROVIDER, "")
if not key:
    print("   No API key found in .env for this provider (fine if you only use the baseline engine).")
elif config.PROVIDER == "manual":
    print("   Manual (copy-paste) mode: no key needed.")
else:
    print("   Key found. Testing one small AI call...")
    from src.llm import ask_llm
    try:
        print("   AI replied:", ask_llm('Reply with exactly this JSON: {"status": "OK"}', run_id=0, use_cache=False)[:80])
    except Exception as e:
        print("   AI call FAILED:", e)
        print("   Check the key, the model name in .env, and your internet connection.")
print("\nDone.")
