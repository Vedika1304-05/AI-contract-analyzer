"""
list_models.py - shows which Gemini models YOUR API key can use, so you can set GEMINI_MODEL correctly.
   python list_models.py
Then copy one model name (for example a 'flash' model) into your .env file:  GEMINI_MODEL=<name>
(The name may be shown as 'models/xyz'. Use just 'xyz'.)
"""
from src import config

if not config.GEMINI_API_KEY:
    raise SystemExit("GEMINI_API_KEY is empty. Put your Google AI Studio key in the .env file first.")
try:
    from google import genai
except ImportError:
    raise SystemExit("The google-genai library is not installed in this Python.\n"
                     "Run:  python -m pip install google-genai")

client = genai.Client(api_key=config.GEMINI_API_KEY)
print("Models your key can use for generating text:\n")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if not actions or "generateContent" in actions:
        print("  ", m.name.replace("models/", ""))
print("\nCurrently set in .env:", config.GEMINI_MODEL)
