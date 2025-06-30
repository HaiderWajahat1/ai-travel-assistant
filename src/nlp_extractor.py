import re
import spacy
from typing import Dict, Optional
from rapidfuzz.fuzz import ratio

nlp = spacy.load("en_core_web_sm")

def extract_location_info(text: str) -> Dict[str, Optional[str]]:
    data = {
        "origin": None,
        "destination": None,
        "flight_number": None,
        "departure_time": None,
        "departure_date": None
    }

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    lower_lines = [line.lower() for line in lines]

    # 🔍 Scan for lines like: "From" → next line = origin
    for i, line in enumerate(lower_lines):
        if is_similar("from", line) and i + 1 < len(lines):
            data["origin"] = lines[i + 1].strip().upper()
        elif is_similar("to", line) and i + 1 < len(lines):
            data["destination"] = lines[i + 1].strip().upper()


    # 🔁 Fallback to spaCy NER if anything still missing
    doc = nlp(text.replace("\n", " "))
    locations = [ent.text.strip().upper() for ent in doc.ents if ent.label_ in ["GPE", "LOC", "FAC"]]
    locations = list(dict.fromkeys(locations))  # dedup

    if not data["origin"] and len(locations) >= 1:
        data["origin"] = locations[0]
    if not data["destination"] and len(locations) >= 2:
        data["destination"] = locations[1]

    # ✈️ Flight number
    flight_match = re.search(r"\b([A-Z]{1,2}\s?\d{3,5})\b", text)
    if flight_match:
        data["flight_number"] = flight_match.group().replace(" ", "")

    # ⏰ Departure time
    time_match = re.search(r"\b\d{2}[:*]\d{2}\b", text)
    if time_match:
        data["departure_time"] = time_match.group().replace("*", ":")

    # 📅 Departure date (supports 09JUN, 30 JUN 2025)
    date_match = re.search(r"\b\d{1,2}\s*[A-Z]{3,9}(?:\s?\d{4})?\b", text, re.IGNORECASE)
    if date_match:
        data["departure_date"] = date_match.group().upper()

    return data

def is_similar(a, b, threshold=85):
    return ratio(a.lower(), b.lower()) >= threshold


