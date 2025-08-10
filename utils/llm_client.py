# utils/llm_client.py
import os, json
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import google.generativeai as genai

_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

def _get_model(system_instruction: str = ""):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Put it in a .env file or your shell env.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=_GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0
        }
    )

def gemini_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Calls Gemini and enforces JSON response (via response_mime_type).
    """
    model = _get_model(system_prompt)
    resp = model.generate_content(user_prompt)
    try:
        return json.loads(resp.text)
    except Exception:
        return {"error": "Invalid JSON from Gemini", "raw": resp.text}
