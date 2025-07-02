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
            "temperature": 1,
            "topK": 32,
            "topP": 1,
            "maxOutputTokens": 2048,
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
