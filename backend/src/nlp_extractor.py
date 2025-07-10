from .gemma_client import call_gemma
from config.prompts import format_travel_prompt
from src.city_corrector import correct_city_name_dynamic

def extract_location_info(text: str) -> dict:
    """
    Extracts structured travel info (origin, destination, flight number, etc.)
    using an LLM, and corrects city names if needed.
    """
    prompt = format_travel_prompt(text)
    result = call_gemma(prompt)

    if isinstance(result, dict):
        if "origin" in result and isinstance(result["origin"], str):
            result["origin"] = correct_city_name_dynamic(result["origin"])
        if "destination" in result and isinstance(result["destination"], str):
            result["destination"] = correct_city_name_dynamic(result["destination"])

    return result