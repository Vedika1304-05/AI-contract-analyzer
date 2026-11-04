"""
llm.py - the ONLY file that talks to an AI provider.
Everything else calls ask_llm(prompt). To change provider, change PROVIDER in your .env file.
Every answer is saved in the cache/ folder, so repeating a run costs nothing and gives the same result.
(To get a genuinely fresh answer for a repeat run, use a different run_id.)
"""
import hashlib
import json
import time
from . import config


def _cache_path(prompt: str, run_id: int):
    model = {"gemini": config.GEMINI_MODEL, "anthropic": config.ANTHROPIC_MODEL,
             "openai": config.OPENAI_MODEL}.get(config.PROVIDER, "manual")
    key = hashlib.sha256(f"{config.PROVIDER}|{model}|{run_id}|{prompt}".encode()).hexdigest()[:24]
    folder = config.CACHE_DIR / "llm"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{key}.json"


# ------------------------------------------------------------------ provider calls
def _call_gemini(prompt: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model="gemini-3.5-flash-lite", contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"))
    return resp.text


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(model=config.ANTHROPIC_MODEL, max_tokens=1500,
                                 messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}])
    return resp.choices[0].message.content


def _call_manual(prompt: str) -> str:
    """Copy-paste mode: you paste the prompt into any chat AI, then paste its answer back here."""
    folder = config.OUTPUT_DIR / "manual_prompts"
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / f"prompt_{hashlib.md5(prompt.encode()).hexdigest()[:8]}.txt"
    f.write_text(prompt, encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"The prompt was saved to: {f}")
    print("1) Open that file, copy ALL of it, paste it into a chat AI (Claude / ChatGPT / Gemini).")
    print("2) Copy the AI's JSON answer and paste it below.")
    print("3) On a NEW line type END and press Enter.")
    print("=" * 70)
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


_PROVIDERS = {"gemini": _call_gemini, "anthropic": _call_anthropic,
              "openai": _call_openai, "manual": _call_manual}


# ------------------------------------------------------------------ the one function you use
def ask_llm(prompt: str, run_id: int = 1, use_cache: bool = True) -> str:
    if config.PROVIDER not in _PROVIDERS:
        raise ValueError(f"Unknown PROVIDER '{config.PROVIDER}'. Use one of: {list(_PROVIDERS)}")

    cache = _cache_path(prompt, run_id)
    if use_cache and config.PROVIDER != "manual" and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["response"]

    last_error = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            text = _PROVIDERS[config.PROVIDER](prompt)
            if config.PROVIDER != "manual":
                cache.write_text(json.dumps({"response": text}), encoding="utf-8")
                time.sleep(config.SLEEP_SECONDS)       # be polite to the free tier
            return text
        except ImportError as e:                         # library not installed in THIS Python
            raise RuntimeError(
                f"A required library is missing for provider '{config.PROVIDER}': {e}\n"
                "Fix: make sure your virtual environment is active (you should see (venv) in the terminal), then run\n"
                "  gemini:    python -m pip install google-genai\n"
                "  anthropic: python -m pip install anthropic\n"
                "  openai:    python -m pip install openai") from e
        except Exception as e:                           # network error, rate limit, bad key ...
            last_error = e
            wait = 5 * attempt
            print(f"   AI call failed (attempt {attempt}/{config.MAX_RETRIES}): {e}. Waiting {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"AI call failed after {config.MAX_RETRIES} attempts: {last_error}")
