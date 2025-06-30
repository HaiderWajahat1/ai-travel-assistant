import re
import spacy
from typing import Dict, Optional
from rapidfuzz import process

nlp = spacy.load("en_core_web_sm")

def extract_location_info(text: str) -> Dict[str, Optional[str]]:
    data = {
        "origin": None,
        "destination": None,
        "flight_number": None,
        "arrival_time": None,
        "arrival_date": None
    }

    # Step 1: Normalize lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    lower_lines = [line.lower() for line in lines]

    # Step 2: Detect keywords "from", "to" with fuzzy match
    def is_similar(a: str, b: str) -> bool:
        return a.lower() in b.lower()

    for i, line in enumerate(lower_lines):
        if is_similar("from", line) and i + 1 < len(lines):
            data["origin"] = lines[i + 1].strip().upper()
        elif is_similar("to", line) and i + 1 < len(lines):
            data["destination"] = lines[i + 1].strip().upper()

    # Step 3: spaCy fallback (if anything missing)
    doc = nlp(text.replace("\n", " "))
    locations = [ent.text.strip().upper() for ent in doc.ents if ent.label_ in ["GPE", "LOC", "FAC"]]
    locations = list(dict.fromkeys(locations))

    if not data["origin"] and len(locations) >= 1:
        data["origin"] = locations[0]
    if not data["destination"] and len(locations) >= 2:
        data["destination"] = locations[1]

    # Step 4: Flight number (e.g., F 0575 or EK702)
    flight_match = re.search(r"\b([A-Z]{1,2}\s?\d{3,5})\b", text)
    if flight_match:
        data["flight_number"] = flight_match.group().replace(" ", "")

    # Step 5: Arrival time — try to extract from lines containing "arrival"
    arrival_time = None
    for line in lines:
        if "arrival" in line.lower():
            match = re.search(r"\b\d{2}[:*]?\d{2}\b", line)
            if match:
                arrival_time = match.group().replace("*", ":")
                break

    # Fallback: use last time in the whole text
    if not arrival_time:
        time_matches = re.findall(r"\b\d{2}[:*]?\d{2}\b", text)
        if time_matches:
            arrival_time = time_matches[-1].replace("*", ":")

    data["arrival_time"] = arrival_time

    # Step 6: Arrival date — take the LAST valid date found
    date_matches = re.findall(r"\b\d{1,2}\s?[A-Z]{3}(?:\s?\d{4})?\b", text.upper())
    if date_matches:
        data["arrival_date"] = date_matches[-1].replace(" ", "")

    return data