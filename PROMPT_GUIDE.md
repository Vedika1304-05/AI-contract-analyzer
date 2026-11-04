# Prompt pack - versions v1 to v5

## Install (2 minutes)
1. Copy `prompts/extract_v2.txt` ... `extract_v5.txt` into your project's `prompts/` folder (v1 is already there).
2. Copy `src/hints.py`, `src/extractor.py`, `src/llm.py` into your project's `src/` folder (replace the old extractor.py and llm.py).
3. Copy `list_models.py` into the project's main folder.
4. In `.env` set `PROMPT_VERSION=extract_v2` (then v3, v4, v5 as you test them).

## What each version adds
| Version | Adds | Why it should help |
|---|---|---|
| v1 | Basic rules + JSON | Your starting point |
| v2 | Vocabulary of synonyms, "operative value" rule, blank/placeholder rule, "excluded" rule, fractions | Fixes missed clauses caused by different wording; stops guessing on blanks |
| v3 | v2 + clause-specific reading guide (hints.py) + short written evidence analysis before the answer | Stops cap-as-rate, employer-vs-contractor damages, bid-vs-performance-security mix-ups; reasoning is saved in the result |
| v4 | v3 + four invented worked examples | Shows the exact output format and tricky cases (cap, blank, excluded, per-day rate) |
| v5 | v4 + final self-audit checklist + confidence rubric | Catches quote/number mismatches before the answer leaves the AI |

## Experiment log (copy into your AI log / validation report)
| Prompt version | Contract (train only) | Correct | Incorrect | Missed | Invented | Unverified quotes | Recall | Precision | Notes |
|---|---|---|---|---|---|---|---|---|---|
| v1 | | | | | | | | | |
| v2 | | | | | | | | | |
| v3 | | | | | | | | | |
| v4 | | | | | | | | | |
| v5 | | | | | | | | | |

## Rules
* Compare versions on TRAIN contracts only, using your mini answer key. Never on test contracts.
* Change one thing at a time. If a later version is worse, keep the earlier one.
* The worked examples in v4/v5 are invented. If you add examples, write them yourself or take them from TRAIN
  contracts only - copying wording from a TEST contract would make your test results dishonest.
* A better prompt cannot fix a retrieval miss. If notes say "no text matching keywords", fix keywords in config.py,
  or raise --top-k (try 8).
