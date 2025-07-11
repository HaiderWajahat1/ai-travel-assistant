from rapidfuzz import process
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITY_FILE_PATH = os.path.join(BASE_DIR, "data", "worldcities.csv")

city_df = pd.read_csv(CITY_FILE_PATH)
CITY_LIST = city_df['city'].dropna().unique().tolist()

def correct_city_name_dynamic(name: str, score_threshold: float = 85.0) -> str:
    """
    Attempts to correct a potentially misspelled city name using fuzzy string matching.

    This function compares the input city name to a list of known world cities
    (from worldcities.csv) using RapidFuzz. If a sufficiently close match is found,
    it returns the corrected city name; otherwise, it returns the original.

    Args:
        name (str): The city name to check and correct.
        score_threshold (float, optional): The minimum similarity score (0–100)
                                           required to consider a match valid.
                                           Default is 85.0.

    Returns:
        str: The corrected city name if a close match is found, otherwise the original name.
    """
    name = name.strip().title()
    match = process.extractOne(name, CITY_LIST, score_cutoff=score_threshold)
    return match[0] if match else name
