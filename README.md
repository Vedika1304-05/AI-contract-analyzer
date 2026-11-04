# AI Contract Analyser for Financial Risk Clauses (CE725 course project)

Reads a construction contract PDF, extracts six financial clause types with an AI (or a simple rules-only
baseline), checks that every quote really exists in the contract, flags risks, and turns the terms into a
monthly cash flow with peak funding and overdraft interest.

## Quick start (after you have installed Python and made a virtual environment)
    pip install -r requirements.txt
    pip install google-genai            # or: anthropic / openai  (only the one you use)
    copy .env.example to .env and fill in your key        (Windows: copy .env.example .env)
    python check_setup.py                                  # is everything ready?
    python check_cashflow.py                               # compare with your Excel benchmark
    python run_extraction.py --pdf data/train/YOURFILE.pdf --engine baseline
    python run_extraction.py --pdf data/train/YOURFILE.pdf --engine llm --run 1
    streamlit run app.py                                   # the screen

## Files
| File | Job |
|---|---|
| src/config.py | all settings, the 6 clause types and their keywords |
| src/pdf_reader.py | PDF -> text per page (cached) |
| src/retrieval.py | cut text into chunks; pick the best chunks for each clause |
| src/llm.py | the ONLY file that talks to the AI provider (change provider in .env) |
| prompts/extract_v1.txt | the instruction given to the AI (version it: v2, v3 ...) |
| src/extractor.py | asks the AI, reads its JSON answer, validates it |
| src/verifier.py | checks the AI's quote exists in the contract (anti-hallucination) |
| src/baseline.py | no-AI rules extractor for comparison |
| src/risk_rules.py | editable risk thresholds + plain-language summary |
| src/cashflow.py | monthly cash flow model (same rules as your Excel benchmark) |
| src/pipeline.py | joins all the steps together |
| src/evaluate.py | scores the tool against your manual answer key |
| run_extraction.py / run_evaluation.py | command-line scripts |
| app.py | Streamlit app |

## Rules of the project
* Improve prompts and code using the TRAIN contracts only. Use TEST contracts once, at the end.
* Every extracted value must be verified by a human against the original contract.
* Log every significant AI prompt in the AI usage log.
