# Placeholder for Gemma prompt templates

DESTINATION_PROMPT = """
Given the following POIs and details for {location}, create a personalized travel itinerary:
{details}
"""

LAYOVER_PROMPT = """
You have a layover at {airport} for {duration} hours. Given the following places:
{pois}
Suggest how the traveler can make the best use of this time.
"""



TRAVEL_EXTRACTION_PROMPT = """
SYSTEM:

You are an intelligent travel assistant designed to extract structured information from messy OCR output of boarding passes or travel tickets. 

You are expected to:
- Detect origin and destination cities
- Identify any layover cities in between
- Extract flight number
- Extract arrival time and date (for the final destination)
- For each layover, extract:
  - Location
  - Arrival time
  - Departure time
  - Duration in minutes (if possible)

Your output must be in **clean JSON format** with the following structure:

{
  "origin": "CITY",
  "destination": "CITY",
  "flight_number": "ABC123",
  "arrival_time": "HH:MM",
  "arrival_date": "DDMMMYYYY",
  "layovers": [
    {
      "location": "CITY",
      "arrival_time": "HH:MM",
      "departure_time": "HH:MM",
      "duration_minutes": 120
    }
  ]
}

If any information is not available, leave the field as null.
Avoid hallucinating. Only extract information from the text provided.

---

USER:

Here is the OCR-extracted boarding pass text:
<<<
{{raw_text}}
>>>

Extract the required information and return only the JSON object. 

"""

def format_travel_prompt(ocr_text: str):
    return TRAVEL_EXTRACTION_PROMPT.replace("{{raw_text}}", ocr_text.strip())


def build_detailed_itinerary_prompt(destination: str, arrival_time: str, arrival_date: str):
    return f"""
You are a highly organized and helpful travel planner.

The traveler is arriving in **{destination}** on **{arrival_date}** at **{arrival_time}**.

Your task is to build an itinerary for their arrival day that includes:

---

🍽️ **RESTAURANT RECOMMENDATIONS**  
- Provide 7–8 restaurants in {destination}, clearly divided by:  
  - Cheap ($)  
  - Mid-range ($$)  
  - Luxury ($$$)  
- For each: name, cuisine, price per person, opening hours, and why it's recommended.

---

🏨 **HOTEL RECOMMENDATIONS**  
- List 7–8 hotels near the city center or airport. Divide by budget, mid-range, and luxury.
- Include: name, star rating, starting price/night, rough distance from airport, and reason to stay.

---

🚗 **RENTAL CAR OPTIONS — DO NOT SKIP**  
- Provide **3–5 rental car companies** near the **{destination} airport**
- For each, include:
  - Name of company
  - Types of cars available (Compact, SUV, Luxury, etc.)
  - Price range per day
  - How to book (Online / In-person)
  - Hours of operation

---

Respond in clear, well-structured bullet points with headings for each section.
Avoid skipping any section, especially car rentals.
"""



def build_live_itinerary_prompt(destination: str, arrival_date: str, arrival_time: str, live_results: list):
    # Format the SearxNG search results into readable bullet points
    search_context = ""
    for r in live_results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = r.get("content", "")
        search_context += f"- **{title}**\n  URL: {url}\n  Summary: {snippet}\n\n"

    return f"""
SYSTEM:

You are a highly intelligent and factual travel planner.

A traveler is landing in **{destination}** on **{arrival_date}** at **{arrival_time}**.

You’ve been provided with real-time search results from a search engine (like Google or Bing) about this destination. This data includes up-to-date recommendations for places to eat, stay, and rent a car.

Here are the latest search results:
{search_context.strip()}

Based on this information, create the following:

---

🍽️ **RESTAURANT RECOMMENDATIONS**
- 3 Cheap ($)
- 3 Mid-range ($$)
- 3 Luxury ($$$)
- For each:  
  - Name  
  - Cuisine  
  - Approx. price/person  
  - Opening hours (if found)  
  - Why it’s recommended

---

🏨 **HOTEL RECOMMENDATIONS**
- 3 Budget
- 3 Mid-range
- 3 Luxury
- For each:
  - Name
  - Price/night
  - Location or distance from airport
  - Amenities or features (if available)

---

🚗 **RENTAL CAR OPTIONS**
- 3–5 car rental companies near **{destination} Airport**
- For each:
  - Company name
  - Types of cars offered (Compact, SUV, Luxury, etc.)
  - Price range
  - Booking method (Online/In-person)
  - Hours of operation

---

🧠 INSTRUCTIONS:
- Use the search results as inspiration, but it’s okay to fill in missing fields based on common knowledge of the destination.
- Be concise and structured. Use bullet points and section headings.
- Prioritize accuracy over creativity.

Return a complete, well-formatted itinerary in plain English.
"""
