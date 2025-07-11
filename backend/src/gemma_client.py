import os
import httpx
import json
import re
import yaml
from dotenv import load_dotenv

load_dotenv()

# Load YAML config
with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
GEMMA_API_URL = config["GEMMA_API_URL"]

def call_gemma(prompt: str) -> dict:
    """
    Sends a prompt to the Gemma 3 27B LLM API and returns the model's response.

    This function sends a structured request to the Gemma API using a user prompt.
    If the response is JSON-like, it attempts to parse and return it. Otherwise,
    it returns the raw text inside an 'output' key.

    Args:
        prompt (str): The prompt string to send to the Gemma model.

    Returns:
        dict: A dictionary containing either parsed JSON or the raw text output.
              If an error occurs, returns {'error': <message>}.
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
    Extracts concise, search-worthy keywords from a list of user preferences
    using the Gemma LLM.

    This function combines the user's preferences into a single prompt and
    queries the Gemma model to return keywords as a comma-separated list.

    Args:
        preferences (list[str]): A list of user-provided preferences such as
                                 "food", "hiking", "no hotel", etc.

    Returns:
        list[str]: A list of extracted keywords (e.g., ["street art", "cafes", "hiking"]).
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
