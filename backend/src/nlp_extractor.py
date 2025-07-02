import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from .gemma_client import call_gemma
from config.prompts import format_travel_prompt

def extract_location_info(text: str) -> dict:
    prompt = format_travel_prompt(text)
    result = call_gemma(prompt)
    return result
