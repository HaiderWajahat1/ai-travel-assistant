from rapidfuzz import process
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITY_FILE_PATH = os.path.join(BASE_DIR, "data", "worldcities.csv")

city_df = pd.read_csv(CITY_FILE_PATH)
CITY_LIST = city_df['city'].dropna().unique().tolist()

def correct_city_name_dynamic(name: str, score_threshold: float = 85.0) -> str:
    """
    Attempts to correct a potentially misspelled city name using fuzzy matching.
    Returns the best match if above threshold, otherwise returns the original.
    """
    name = name.strip().title()
    match = process.extractOne(name, CITY_LIST, score_cutoff=score_threshold)
    return match[0] if match else name
