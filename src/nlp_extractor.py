import re
import spacy
from typing import Dict, Optional, List, Union
from datetime import datetime

nlp = spacy.load("en_core_web_sm")

def parse_time(t: str) -> Optional[datetime]:
    try:
        return datetime.strptime(t.replace("*", ":"), "%H:%M")
    except:
        return None

def extract_location_info(text: str) -> Dict[str, Union[str, None, List[Dict]]]:
    data = {
        "origin": None,
        "destination": None,
        "flight_number": None,
        "arrival_time": None,
        "arrival_date": None,
        "layovers": "N/A"
    }

    # Step 1: Preprocess
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    doc = nlp(text.replace("\n", " "))

    # Step 2: Extract all locations (GPE, LOC, FAC)
    locations = [ent.text.strip().upper() for ent in doc.ents if ent.label_ in ["GPE", "LOC", "FAC"]]
    locations = list(dict.fromkeys(locations))  # unique

    if len(locations) >= 1:
        data["origin"] = locations[0]
    if len(locations) >= 2:
        data["destination"] = locations[-1]
    if len(locations) > 2:
        layover_locs = locations[1:-1]
    else:
        layover_locs = []

    # Step 3: Flight number
    flight_match = re.search(r"\b([A-Z]{1,2}\s?\d{3,5})\b", text)
    if flight_match:
        data["flight_number"] = flight_match.group().replace(" ", "")

    # Step 4: All time strings
    all_times = re.findall(r"\b\d{1,2}[:*]?\d{2}\s?(?:AM|PM|am|pm)?\b", text)
    clean_times = [t.replace("*", ":").upper().strip() for t in all_times]

    # Step 5: All date strings
    date_match = re.search(r"\b\d{1,2}\s?[A-Z]{3,9}\s?\d{2,4}\b", text.upper())
    if date_match:
        data["arrival_date"] = date_match.group().replace(" ", "").upper()

    # Step 6: Improved layover matching using location-time co-occurrence
    layovers = []

    for i, loc in enumerate(layover_locs):
        arr_time = None
        dep_time = None
        for line in lines:
            if loc in line.upper():
                times_in_line = re.findall(r"\b\d{1,2}[:*]?\d{2}\s?(?:AM|PM|am|pm)?\b", line)
                if len(times_in_line) == 2:
                    arr_time = times_in_line[0].replace("*", ":").upper()
                    dep_time = times_in_line[1].replace("*", ":").upper()
                    break
                elif len(times_in_line) == 1:
                    arr_time = times_in_line[0].replace("*", ":").upper()
        # fallback if still empty
        if not dep_time and i + 1 < len(clean_times):
            dep_time = clean_times[i + 1]
        if not arr_time and i < len(clean_times):
            arr_time = clean_times[i]

        duration = None
        t1 = parse_time(arr_time) if arr_time else None
        t2 = parse_time(dep_time) if dep_time else None
        if t1 and t2:
            duration = (t2 - t1).seconds // 60

        layovers.append({
            "location": loc,
            "arrival_time": arr_time,
            "departure_time": dep_time,
            "duration_minutes": duration
        })

    data["layovers"] = layovers if layovers else "N/A"

    # Step 7: Arrival time → last time in doc
    if clean_times:
        data["arrival_time"] = clean_times[-1]

    return data
