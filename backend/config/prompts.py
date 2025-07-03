import re
from collections import defaultdict
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


# # Helper for extracting price info from a snippet
# def extract_price(text):
#     match = re.search(
#         r"(\$\$?\$?)|from\s*\$\d+|starting at\s*\$\d+|\$\d+(\.\d{2})?",
#         text
#     )
#     if match:
#         return match.group(0)
#     return None


# # new one innit 

# def build_live_itinerary_prompt(destination: str, arrival_time: str, arrival_date: str, search_results: list) -> str:
#     prompt = f"""
# You are a travel assistant AI helping a traveler plan their arrival-day experience.

# The traveler is landing in **{destination}** on **{arrival_date}** at **{arrival_time}**.

# You are given a set of **web search results** related to this destination. Use these results to generate your response.

# ---

# ### 🧠 Hybrid Logic:

# - **Step 1:** You must identify relevant results by scanning for key terms.
#   - Use search results mentioning **food, cafes, pizza, tacos, dining, bistro, etc.** for the Restaurants section.
#   - Use search results mentioning **hotels, lodging, accommodation, check-in, price per night, etc.** for the Hotels section.
#   - Use search results mentioning **car rentals, SUVs, sedans, compact, Hertz, Avis, pickup, etc.** for the Rental Cars section.

#   If you find no relevant search result in a category, then (and only then) fall back to internal knowledge and label it as `Fallback (LLM)`.

# - **Step 2:** If any category (e.g. Cheap restaurants) has no useful data, use your internal knowledge as a fallback — but clearly mark those entries with `Fallback` so the user knows they came from your knowledge base, not the web.
# - **Step 3:** Structure the final output as a clean Markdown-formatted itinerary with 3 recommendations per category, if possible.

# ---

# ### 📋 Output Instructions:

# 1. **Restaurants**
#    - Use only results tagged as `"restaurant"` for this section.
#    - For each: name, brief description, price (if present), and website (if present).
#    - If no relevant snippets are found, use `Fallback (LLM)` entries, and link to a Google search for the place.

# 2. **Hotels**
#    - Use only results tagged as `"hotel"` for this section.
#    - For each: name, price/night (if present), location, website (if present).
#    - If no relevant snippets are found, use `Fallback (LLM)` entries, and link to a Google search for the hotel.

# 3. **Rental Cars**
#    - Use only results tagged as `"rental"` for this section.
#    - For each: brand, types of cars, booking method, pickup info, website (if present).
#    - If no relevant snippets are found, use `Fallback (LLM)` entries.

# For each category, **only use Fallback (LLM)** if no web result includes relevant info. Do not skip web data if any match exists, even partial.

#   Please carefully match relevant content to each section. For example:
# - If a snippet mentions tacos or food, use it in the Restaurants section.
# - If a snippet mentions a hotel name, price, or amenities, use it in the Hotels section.
# - If it lists rental companies or pickup details, use it in Car Rentals.

# ✅ Clearly label whether each recommendation is:
# - `From Search Result X`
# - or `Fallback (LLM)`

# ---

# 🔍 **Search Results**:
# """
#     grouped = {
#         "restaurant": [],
#         "hotel": [],
#         "rental": [],
#         "general": []
#     }

#     for result in search_results:
#         category = result.get("category", "general")
#         grouped.setdefault(category, []).append(result)

#     # RESTAURANTS
#     prompt += "\n### 🍽️ Restaurants\n"
#     if grouped['restaurant']:
#         for i, result in enumerate(grouped['restaurant']):
#             price_info = extract_price(result.get('content', ''))
#             prompt += (
#                 f"- **{result.get('title', '')}** `From Search Result {i+1}`\n"
#                 f"  {result.get('content', '')}\n"
#             )
#             if price_info:
#                 prompt += f"  **Price:** {price_info}\n"
#             else:
#                 prompt += "  _(Price info not listed, check website for details)_\n"
#             if result.get("url"):
#                 prompt += f"  [Website]({result.get('url')})\n"
#     else:
#         # Example LLM fallback items (customize/expand as needed)
#         fallback_restaurants = [
#             "Joe's Pizza", "Superiority Burger", "Shake Shack"
#         ]
#         for name in fallback_restaurants:
#             google_link = f"https://www.google.com/search?q={name.replace(' ', '+')}+NYC"
#             prompt += (
#                 f"- **{name}** `Fallback (LLM)`\n"
#                 f"  _(No price info available)_\n"
#                 f"  [Website]({google_link})\n"
#             )

#     # HOTELS
#     prompt += "\n### 🏨 Hotels\n"
#     if grouped['hotel']:
#         for i, result in enumerate(grouped['hotel']):
#             price_info = extract_price(result.get('content', ''))
#             prompt += (
#                 f"- **{result.get('title', '')}** `From Search Result {i+1}`\n"
#                 f"  {result.get('content', '')}\n"
#             )
#             if price_info:
#                 prompt += f"  **Price:** {price_info}\n"
#             else:
#                 prompt += "  _(Price info not listed, check website for details)_\n"
#             if result.get("url"):
#                 prompt += f"  [Website]({result.get('url')})\n"
#     else:
#         fallback_hotels = [
#             "The Jane Hotel", "Pod 39", "The Library Hotel"
#         ]
#         for name in fallback_hotels:
#             google_link = f"https://www.google.com/search?q={name.replace(' ', '+')}+NYC+hotel"
#             prompt += (
#                 f"- **{name}** `Fallback (LLM)`\n"
#                 f"  _(No price info available)_\n"
#                 f"  [Website]({google_link})\n"
#             )

#     # RENTAL CARS
#     prompt += "\n### 🚗 Rental Cars\n"
#     if grouped['rental']:
#         for i, result in enumerate(grouped['rental']):
#             prompt += (
#                 f"- **{result.get('title', '')}** `From Search Result {i+1}`\n"
#                 f"  {result.get('content', '')}\n"
#             )
#             if result.get("url"):
#                 prompt += f"  [Website]({result.get('url')})\n"
#     else:
#         fallback_rentals = [
#             "Hertz", "Avis", "Enterprise"
#         ]
#         for name in fallback_rentals:
#             google_link = f"https://www.google.com/search?q={name.replace(' ', '+')}+NYC+car+rental"
#             prompt += (
#                 f"- **{name}** `Fallback (LLM)`\n"
#                 f"  [Website]({google_link})\n"
#             )

#     prompt += """

# ---

# Now, using the **above search results first**, and your own knowledge *only when necessary*, generate a well-structured Markdown itinerary. Do not hallucinate URLs or make up fake brands. Always mention whether each suggestion came from `Search Result X` or is a `Fallback (LLM)`.

# """
#     return prompt

# experiment here for 3 and 3 


import re
from collections import defaultdict

def extract_price(text):
    match = re.search(
        r"(\$\$?\$?)|from\s*\$\d+|starting at\s*\$\d+|\$\d+(\.\d{2})?",
        text
    )
    if match:
        return match.group(0)
    return None

def guess_price_range(text):
    text = text.lower()
    # For both restaurants and hotels
    if "$$$" in text or "fine dining" in text or "michelin" in text or "luxury" in text or "five-star" in text or "expensive" in text or "suite" in text or "penthouse" in text:
        return "$$$"
    if "$$" in text or "mid-range" in text or "bistro" in text or "popular" in text or "moderate" in text or "brasserie" in text or "boutique" in text or "modern" in text or "4-star" in text:
        return "$$"
    if "$" in text or "affordable" in text or "cheap" in text or "budget" in text or "fast food" in text or "pizza" in text or "diner" in text or "casual" in text or "hostel" in text or "basic" in text or "value" in text:
        return "$"
    return None

def categorize_by_price(results, is_restaurant=True):
    grouped = defaultdict(list)
    for res in results:
        price = extract_price(res.get('content', '')) or guess_price_range(res.get('content', '')) or guess_price_range(res.get('title', ''))
        if price == "$$$":
            grouped["Luxury"].append(res)
        elif price == "$$":
            grouped["Mid-Range"].append(res)
        elif price == "$":
            grouped["Cheap"].append(res)
        else:
            grouped["Mid-Range"].append(res)  # Default if no info
    return grouped

def build_live_itinerary_prompt(destination: str, arrival_time: str, arrival_date: str, search_results: list) -> str:
    prompt = f"""
You are a travel assistant AI helping a traveler plan their arrival-day experience.

The traveler is landing in **{destination}** on **{arrival_date}** at **{arrival_time}**.

You are given a set of **web search results** related to this destination. Use these results to generate your response.

---

### 🧠 Hybrid Logic:

- Categorize restaurants and hotels as Cheap, Mid-Range, and Luxury using price info or cues.
- Show up to 3 recommendations per tier.
- Show a clickable website for each.
- Use internal knowledge (Fallback LLM) only if web results for a tier are missing.

---

### 🍽️ Restaurants
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

    # Restaurants - by tier
    if grouped['restaurant']:
        categorized = categorize_by_price(grouped['restaurant'], is_restaurant=True)
        for tier in ["Cheap", "Mid-Range", "Luxury"]:
            prompt += f"\n#### {tier}\n"
            items = categorized[tier]
            if items:
                for i, result in enumerate(items[:3]):
                    price_info = extract_price(result.get('content', '')) or guess_price_range(result.get('content', '')) or guess_price_range(result.get('title', ''))
                    prompt += (
                        f"- **{result.get('title', '')}** `From Search Result {i+1}`\n"
                        f"  {result.get('content', '')}\n"
                        f"  **Estimated Price:** {price_info if price_info else 'Not listed'}\n"
                    )
                    if result.get("url"):
                        prompt += f"  [Website]({result.get('url')})\n"
            else:
                prompt += "_No options found in this tier._\n"
    else:
        # Fallback for restaurants: adjust names as needed
        fallback = {
            "Cheap": ["Joe's Pizza", "Superiority Burger", "Mamoun's Falafel"],
            "Mid-Range": ["Shake Shack", "The Smith", "ABC Kitchen"],
            "Luxury": ["Le Bernardin", "Per Se", "Guy Savoy"]
        }
        for tier in ["Cheap", "Mid-Range", "Luxury"]:
            prompt += f"\n#### {tier}\n"
            for name in fallback[tier]:
                google_link = f"https://www.google.com/search?q={destination.replace(' ', '+')}+restaurant"

                prompt += (
                    f"- **{name}** `Fallback (LLM)`\n"
                    f"  _(No price info available)_\n"
                    f"  [Website]({google_link})\n"
                )

    prompt += "\n### 🏨 Hotels\n"

    # Hotels - by tier
    if grouped['hotel']:
        categorized = categorize_by_price(grouped['hotel'], is_restaurant=False)
        for tier in ["Cheap", "Mid-Range", "Luxury"]:
            prompt += f"\n#### {tier}\n"
            items = categorized[tier]
            if items:
                for i, result in enumerate(items[:3]):
                    price_info = extract_price(result.get('content', '')) or guess_price_range(result.get('content', '')) or guess_price_range(result.get('title', ''))
                    prompt += (
                        f"- **{result.get('title', '')}** `From Search Result {i+1}`\n"
                        f"  {result.get('content', '')}\n"
                        f"  **Estimated Price:** {price_info if price_info else 'Not listed'}\n"
                    )
                    if result.get("url"):
                        prompt += f"  [Website]({result.get('url')})\n"
            else:
                prompt += "_No options found in this tier._\n"
    else:
        fallback = {
            "Cheap": ["The Jane Hotel", "Pod 39", "The Local NYC"],
            "Mid-Range": ["Arlo Hotels", "The Library Hotel", "The Hoxton"],
            "Luxury": ["Four Seasons Hotel", "The Peninsula Paris", "Hotel Plaza Athénée"]
        }
        for tier in ["Cheap", "Mid-Range", "Luxury"]:
            prompt += f"\n#### {tier}\n"
            for name in fallback[tier]:
                google_link = f"https://www.google.com/search?q={destination.replace(' ', '+')}+hotel"
                prompt += (
                    f"- **{name}** `Fallback (LLM)`\n"
                    f"  _(No price info available)_\n"
                    f"  [Website]({google_link})\n"
                )

    prompt += "\n### 🚗 Rental Cars\n"
    if grouped['rental']:
        for i, result in enumerate(grouped['rental']):
            prompt += (
                f"- **{result.get('title', '')}** `From Search Result {i+1}`\n"
                f"  {result.get('content', '')}\n"
            )
            if result.get("url"):
                prompt += f"  [Website]({result.get('url')})\n"
    else:
        fallback_rentals = [
            "Hertz", "Avis", "Enterprise"
        ]
        for name in fallback_rentals:
            google_link = f"https://www.google.com/search?q={destination.replace(' ', '+')}+car+rental"
            prompt += (
                f"- **{name}** `Fallback (LLM)`\n"
                f"  [Website]({google_link})\n"
            )

    prompt += """

---

Now, using the **above search results first**, and your own knowledge *only when necessary*, generate a well-structured Markdown itinerary grouped by Cheap, Mid-Range, and Luxury for both restaurants and hotels. Do not hallucinate URLs or make up fake brands. Always mention whether each suggestion came from `Search Result X` or is a `Fallback (LLM)`.

"""
    return prompt





def build_fallback_prompt(destination: str, arrival_time: str, arrival_date: str) -> str:
    return f"""
You are a travel assistant AI helping a traveler plan their arrival-day experience in **{destination}**, arriving at **{arrival_time}** on **{arrival_date}**.

There are no live web search results available, so you must use your own general knowledge and best judgment.

Your itinerary must be **grouped by price range (Cheap, Mid-Range, Luxury)** for both restaurants and hotels, with each entry using the same structured format as web-based results.

---

## 🍽️ Restaurants

**Please provide three recommendations in each of these categories:**
- **Cheap ($):** Affordable options, e.g. bakeries, bistros, pizza, casual cafés.
- **Mid-Range ($$):** Quality dining at moderate prices, e.g. brasseries, casual fine dining.
- **Luxury ($$$):** High-end, famous, or Michelin-starred restaurants.

For each restaurant, give:
- Name
- Brief description (type of food/cuisine, location or neighborhood, ambiance)
- **Estimated Price:** ($, $$, or $$$)
- A [Google Search link](https://www.google.com/search?q={destination.replace(' ', '+')}+restaurant) for the user to find more info (do NOT make up a direct website)
- Example:

    - **Le Meurice**  
      Elegant fine dining at a Michelin-starred hotel restaurant in the 1st arrondissement.  
      **Estimated Price:** $$$  
      [Google Search](https://www.google.com/search?q=Le+Meurice+{destination.replace(' ', '+')}+restaurant)

---

## 🏨 Hotels

**Provide three recommendations in each of these categories:**
- **Cheap ($):** Budget hotels, hostels, or simple accommodations.
- **Mid-Range ($$):** Reliable chains, boutique or business hotels.
- **Luxury ($$$):** Upscale, famous, or five-star properties.

For each hotel, give:
- Name
- Brief description (type, location/neighborhood, amenities, style)
- **Estimated Price:** ($, $$, or $$$)
- A [Google Search link](https://www.google.com/search?q={destination.replace(' ', '+')}+hotel)
- Example:

    - **The Jane Hotel**  
      Historic budget hotel in the West Village, known for its compact rooms and vintage charm.  
      **Estimated Price:** $  
      [Google Search](https://www.google.com/search?q=The+Jane+Hotel+{destination.replace(' ', '+')}+hotel)

---

## 🚗 Rental Cars

**Provide two or three major car rental agencies with a short note:**
- Name
- General location (e.g., airport/central/train station)
- Types of vehicles available (if known)
- [Google Search link](https://www.google.com/search?q=car+rental+{destination.replace(' ', '+')})

Example:

- **Hertz**  
  Available at the airport and central locations, offers a variety of vehicles from economy to SUV.  
  [Google Search](https://www.google.com/search?q=Hertz+car+rental+{destination.replace(' ', '+')})

---

**Important:**
- Make sure all recommendations are well-known or realistic for a major international city.
- Be concise but informative.
- Output must be **in clean Markdown**, with clear subheadings for each tier.
- Do NOT hallucinate details you are not confident about.
- Do NOT fabricate direct website URLs; always use a Google Search link for further info.

"""

def build_user_query_prompt(user_query, search_results):
    """
    Formats a prompt for Gemma/Gemini that combines user query and web results.
    This reuses your formatting style, lets you tweak in one place.
    """
    web_snippets = ""
    for i, r in enumerate(search_results):
        web_snippets += f"\n[{i+1}] {r.get('title', '')}\n{r.get('content', '')}\n{r.get('url', '')}\n"

    prompt = f"""
You are a travel assistant AI. The user can ask you **any** travel question—logistics, points of interest, airport info, restaurants, itineraries, hiking spots, etc.

Use the recent web search results below for your answer. If the user's question is for an itinerary, organize your answer as a Markdown itinerary (group by price if appropriate). For any other type of question, just answer it directly using both your knowledge and the web results.

User Question:
{user_query}

Recent Web Search Results:
{web_snippets}

Your response must be clear, useful, and formatted in Markdown if appropriate (for example, lists, sections, etc).
If you can't find an answer, say so politely and suggest where the user might look.
"""
    return prompt
