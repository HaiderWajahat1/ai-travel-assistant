import os
import httpx
import json
import re
from dotenv import load_dotenv

load_dotenv()

GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
GEMMA_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemma-3-27b-it:generateContent"

def call_gemma(prompt: str) -> dict:
    """
    Sends a prompt to the Gemma 3 27B LLM API and parses the response.
    Tries to return JSON. If not possible, returns raw output in 'output' key.
    """
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMMA_API_KEY
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "topK": 32,
            "topP": 1,
            "maxOutputTokens": 4000,
        }
    }

    try:
        response = httpx.post(GEMMA_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        content = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        print("\nGEMMA RAW OUTPUT:\n", content)

        if not content:
            return {"error": "Empty response from Gemma"}

        match = re.search(r'\{[\s\S]+\}', content)
        if match:
            content = match.group(0)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"output": content}

    except Exception as e:
        return {"error": f"Gemma call failed: {str(e)}"}


def extract_keywords_from_preferences(preferences: list[str]) -> list[str]:
    """
    Sends preferences to Gemma to extract search-worthy keywords or categories.
    Returns a list of strings like 'street art', 'hiking', etc.
    """
    combined = " ".join(preferences)
    prompt = f"""
You're a smart AI travel assistant.

Your task is to extract keywords or category topics from the following traveler preferences. These should be search-worthy topics like types of attractions, services, or activities.

Only output a comma-separated list. Do NOT include explanations.

Traveler said:
\"\"\"{combined}\"\"\"
"""
    response = call_gemma(prompt)
    raw_text = response.get("output", str(response)) if isinstance(response, dict) else str(response)
    return [x.strip() for x in raw_text.split(",") if x.strip()]
