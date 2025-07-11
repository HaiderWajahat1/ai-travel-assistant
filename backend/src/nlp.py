from src.gemma import call_gemma
from config.prompts import format_travel_prompt
from src.cities import correct_city_name_dynamic

def extract_location_info(text: str) -> dict:
    """
    Extracts structured travel information (e.g., origin, destination, flight number)
    from unstructured OCR text using an LLM. Also corrects detected city names.

    The function sends the cleaned OCR text to Gemma via a formatted prompt,
    then post-processes the results using a city name corrector.

    Args:
        text (str): Raw OCR-extracted text from a travel document (e.g., boarding pass).

    Returns:
        dict: A dictionary containing extracted travel fields. Example keys may include:
              'origin', 'destination', 'flight_number', etc. City names are auto-corrected.
    """
    prompt = format_travel_prompt(text)
    result = call_gemma(prompt)

    if isinstance(result, dict):
        if "origin" in result and isinstance(result["origin"], str):
            result["origin"] = correct_city_name_dynamic(result["origin"])
        if "destination" in result and isinstance(result["destination"], str):
            result["destination"] = correct_city_name_dynamic(result["destination"])

    return result