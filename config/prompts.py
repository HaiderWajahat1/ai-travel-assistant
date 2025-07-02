# Placeholder for Gemma prompt templates

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


# def build_detailed_itinerary_prompt(destination: str, arrival_time: str, arrival_date: str):
#     return f"""
# You are a highly organized and helpful travel planner.

# The traveler is arriving in **{destination}** on **{arrival_date}** at **{arrival_time}**.

# Your task is to build an itinerary for their arrival day that includes:

# ---

# 🍽️ **RESTAURANT RECOMMENDATIONS**  
# - Provide 7–8 restaurants in {destination}, clearly divided by:  
#   - Cheap ($)  
#   - Mid-range ($$)  
#   - Luxury ($$$)  
# - For each: name, cuisine, price per person, opening hours, and why it's recommended.

# ---

# 🏨 **HOTEL RECOMMENDATIONS**  
# - List 7–8 hotels near the city center or airport. Divide by budget, mid-range, and luxury.
# - Include: name, star rating, starting price/night, rough distance from airport, and reason to stay.

# ---

# 🚗 **RENTAL CAR OPTIONS — DO NOT SKIP**  
# - Provide **3–5 rental car companies** near the **{destination} airport**
# - For each, include:
#   - Name of company
#   - Types of cars available (Compact, SUV, Luxury, etc.)
#   - Price range per day
#   - How to book (Online / In-person)
#   - Hours of operation

# ---

# Respond in clear, well-structured bullet points with headings for each section.
# Avoid skipping any section, especially car rentals.
# """


def build_live_itinerary_prompt(destination: str, arrival_time: str, arrival_date: str, search_results: list) -> str:
    prompt = f"""
You are a travel assistant AI helping a traveler plan their arrival-day experience.

The traveler is landing in **{destination}** on **{arrival_date}** at **{arrival_time}**.

You are given a set of **web search results** related to this destination. Use these results to generate your response.

---

### 🧠 Hybrid Logic:

- **Step 1:** You must identify relevant results by scanning for key terms.
  - Use search results mentioning **food, cafes, pizza, tacos, dining, bistro, etc.** for the Restaurants section.
  - Use search results mentioning **hotels, lodging, accommodation, check-in, price per night, etc.** for the Hotels section.
  - Use search results mentioning **car rentals, SUVs, sedans, compact, Hertz, Avis, pickup, etc.** for the Rental Cars section.

  If you find no relevant search result in a category, then (and only then) fall back to internal knowledge and label it as `Fallback (LLM)`.

- **Step 2:** If any category (e.g. Cheap restaurants) has no useful data, use your internal knowledge as a fallback — but clearly mark those entries with `Fallback` so the user knows they came from your knowledge base, not the web.
- **Step 3:** Structure the final output as a clean Markdown-formatted itinerary with 3 recommendations per category, if possible.

---

### 📋 Output Instructions:

1. **Restaurants**
   - Match against relevant search snippets using food-related words (e.g., "tacos", "pizza", "Michelin", "rooftop dining").
   - If no relevant snippets are found, use `Fallback (LLM)` entries.
   - Group by: Cheap ($), Mid-Range ($$), Luxury ($$$)

2. **Hotels**
   - Categories: Budget, Mid-Range, Luxury
   - For each: Give name, price/night, location, and amenities.

3. **Rental Cars**
   - Give 2-3 options: Brand, types of cars, booking method, pickup info.

For each category, **only use Fallback (LLM)** if no web result includes relevant info. Do not skip web data if any match exists, even partial.

  Please carefully match relevant content to each section. For example:
- If a snippet mentions tacos or food, use it in the Restaurants section.
- If a snippet mentions a hotel name, price, or amenities, use it in the Hotels section.
- If it lists rental companies or pickup details, use it in Car Rentals.

✅ Clearly label whether each recommendation is:
- `From Search Result X`
- or `Fallback (LLM)`

---

🔍 **Search Results**:
"""
    grouped = {
    "restaurant": [],
    "hotel": [],
    "rental": [],
    "general": []
    }

    for result in search_results:
        category = result.get("category", "general")
        grouped.setdefault(category, []).append(result)

    # Add categorized results
    for category in ["restaurant", "hotel", "rental"]:
        prompt += f"\n### 🔎 {category.capitalize()} Search Results:\n"
        for i, result in enumerate(grouped[category]):
            prompt += (
                f"\n**{category.capitalize()} Result {i+1}**\n"
                f"- Title: {result.get('title', '')}\n"
                f"- URL: {result.get('url', '')}\n"
                f"- Snippet: {result.get('content', '')}\n"
            )
    prompt += """

---

Now, using the **above search results first**, and your own knowledge *only when necessary*, generate a well-structured Markdown itinerary. Do not hallucinate URLs or make up fake brands. Always mention whether each suggestion came from `Search Result X` or is a `Fallback (LLM)`.

"""
    return prompt

def build_fallback_prompt(destination: str, arrival_time: str, arrival_date: str) -> str:
    return f"""
You are a helpful travel assistant AI helping a traveler plan their arrival-day experience.

They are landing in **{destination}** at **{arrival_time}** on **{arrival_date}**.

Since no live search results were found, you should rely on your general knowledge of the location.

Please provide:
1. Three restaurant recommendations each in the **Cheap ($), Mid-Range ($$), and Luxury ($$$)** categories.
2. Three hotel recommendations in each of the **Budget, Mid-Range, and Luxury** categories.
3. Two or three car rental options near the airport.

For each recommendation, include:
- Name
- Cuisine/Type
- Approx. price range (
- Location or distance (general)
- Why its recommended

Present everything in a clean, structured **Markdown format**, using headings and bullet points. Be detailed but avoid hallucinating facts you’re unsure of. Label all sections clearly and logically.
"""

