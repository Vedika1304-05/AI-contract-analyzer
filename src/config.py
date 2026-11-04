"""
config.py - ALL settings live here.
If you want to change a keyword, a threshold or a model name, this is the first place to look.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")          # reads your secret keys from the .env file

# ---------------------------------------------------------------- AI provider
# Choose ONE in your .env file:  PROVIDER=gemini | anthropic | openai | manual
PROVIDER = os.getenv("PROVIDER", "gemini").lower()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Model names change over time. CHECK the provider's website and override in .env if needed.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "2"))   # pause between AI calls (rate limits)
MAX_RETRIES = 3

# ---------------------------------------------------------------- folders
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "outputs"
PROMPT_DIR = ROOT / "prompts"
for _d in (CACHE_DIR, OUTPUT_DIR, PROMPT_DIR):
    _d.mkdir(exist_ok=True)

# Which prompt file to use. Make a copy called extract_v2.txt when you improve it,
# then set PROMPT_VERSION=extract_v2 in .env (and log the change in your AI log).
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "extract_v1")

# ---------------------------------------------------------------- retrieval settings
TOP_K_CHUNKS = 5          # how many text pieces we send to the AI per clause type
CHUNK_CHARS = 1600        # size of each text piece
CHUNK_OVERLAP_LINES = 3   # lines shared between neighbouring pieces

# ---------------------------------------------------------------- the 6 clause types
# keywords: phrase -> weight (higher = stronger signal that the text is about this clause)
CLAUSES = {
    "payment_terms": {
        "label": "Payment terms (time allowed for the employer to pay a bill)",
        "definition": ("The number of days within which the employer must pay a contractor's interim/running "
                       "bill or certificate after it is submitted or certified. Report the number of days "
                       "and whether they are calendar or working days."),
        "keywords": {"time of payment": 4, "period for honouring": 4, "period for honoring": 4,
                     "payment shall be made within": 4, "shall be paid within": 4, "interim certificate": 2,
                     "interim payment": 2, "running account bill": 2, "running bill": 2,
                     "stage payment": 2, "payment": 1, "certificate of payment": 2, "days of": 0.5},
    },
    "retention": {
        "label": "Retention money / security deposit deducted from bills",
        "definition": ("A percentage deducted from each running bill and held back until completion or the end "
                       "of the defects liability period (also called security deposit, retention money, amount "
                       "withheld). Put the per-bill percentage in numeric_value and any overall maximum "
                       "(e.g. 'total retention not to exceed 5% of contract value') in cap_percent. "
                       "If the contract only has a security deposit deducted from bills, treat it as retention "
                       "and say so in notes."),
        "keywords": {"retention money": 4, "retention": 2, "security deposit": 3, "initial security deposit": 3,
                     "retained": 1, "withheld": 1, "deducted from each": 2, "defects liability": 1},
    },
    "advance": {
        "label": "Mobilisation advance / advance payment",
        "definition": ("An advance paid to the contractor at the start (mobilisation advance, advance payment, "
                       "equipment advance) to be recovered later from bills. Report the percentage of contract "
                       "value in numeric_value. Mention interest on the advance in notes."),
        "keywords": {"mobilisation advance": 5, "mobilization advance": 5, "advance payment": 4,
                     "equipment advance": 3, "secured advance": 1, "mobilisation": 1, "mobilization": 1,
                     "interest on advance": 2},
    },
    "liquidated_damages": {
        "label": "Liquidated damages / compensation for delay (contractor's delay penalty)",
        "definition": ("A pre-agreed amount the CONTRACTOR pays for late completion (also called compensation "
                       "for delay, damages for non-completion, delay damages). Put the rate in numeric_value "
                       "and its unit in unit (e.g. '% per week', '% per day', '% per month'). Put the maximum "
                       "total (cap) as a percentage in cap_percent. Ignore damages payable BY the employer."),
       "keywords": {"liquidated damages": 5, "compensation for delay": 5, "damages for delay": 4,
             "damages for non-completion": 4, "delay damages": 4, "per week": 1,
             "per day of delay": 2, "of delay": 1,
             "for delay of each day": 4, "each day of delay": 3, "pay damages": 3},
    },
    "escalation": {
        "label": "Price escalation / price variation / price adjustment",
        "definition": ("A clause that adjusts the contract price when material, labour or fuel prices change. "
                       "found=true only if such a clause really exists. If the contract states that rates are "
                       "firm / no escalation is allowed, set found=false and explicitly_excluded=true and "
                       "quote that sentence."),
        "keywords": {"price variation": 4, "price adjustment": 4, "price escalation": 4, "escalation": 3,
                     "rates are firm": 4, "no escalation": 5, "firm price": 3, "variation in price": 2,
                     "price index": 2},
    },
    "performance_security": {
        "label": "Performance security / performance bank guarantee",
        "definition": ("A guarantee or deposit the contractor must provide to secure performance. Report the "
                       "percentage of contract price / bid price in numeric_value. Mention if it is a bank "
                       "guarantee and its validity in notes."),
        "keywords": {"performance security": 4, "performance guarantee": 4, "performance bank guarantee": 5,
                     "bank guarantee": 2, "additional performance security": 2, "guarantee": 0.5},
    },
}
