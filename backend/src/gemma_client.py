import os
import httpx
import json
from dotenv import load_dotenv
import re

# Load environment variables from .env
load_dotenv()

# Get API key and URL for Gemma 3 27B
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
GEMMA_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemma-3-27b-it:generateContent"
#GEMMA_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def call_gemma(prompt: str) -> dict:
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

        # 🧪 Debug log (optional)
        print("\n🔍 GEMMA RAW OUTPUT:\n", content)

        # Empty response
        if not content:
            return {"error": "Empty response from Gemma"}
        match = re.search(r'\{[\s\S]+\}', content)
        if match:
            content = match.group(0)
        # Try parsing as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "output": content
            }
        
    except Exception as e:
        return {"error": f"Gemma call failed: {str(e)}"}


def extract_keywords_from_preferences(preferences: list[str]) -> list[str]:
    from .gemma_client import call_gemma  # If not already imported locally

    combined = " ".join(preferences)
    prompt = f"""
You're a smart AI travel assistant.

Your task is to extract keywords or category topics from the following traveler preferences. These should be search-worthy topics like types of attractions, services, or activities.

Examples:
- If input is: "I want to try local beer and visit street art" → Output: beer tasting, street art
- If input is: "I have a dog and want nature walks" → Output: pet-friendly places, nature walks
- If input is: "interested in space science" → Output: science museum

Only output a comma-separated list. Do NOT include explanations.

Traveler said:
\"\"\"{combined}\"\"\"
"""

    response = call_gemma(prompt)

    # In case the LLM wraps it oddly
    if isinstance(response, dict) and "output" in response:
        raw_text = response["output"]
    else:
        raw_text = str(response)

    return [x.strip() for x in raw_text.split(",") if x.strip()]
