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


def extract_price(text):
    match = re.search(
        r"(\$\$?\$?)|from\s*\$\d+|starting at\s*\$\d+|\$\d+(\.\d{2})?",
        text
    )
    if match:
        return match.group(0)
    return None

# def guess_price_range(text):
#     text = text.lower()
#     # For both restaurants and hotels
#     if "$$$" in text or "fine dining" in text or "michelin" in text or "luxury" in text or "five-star" in text or "expensive" in text or "suite" in text or "penthouse" in text:
#         return "$$$"
#     if "$$" in text or "mid-range" in text or "bistro" in text or "popular" in text or "moderate" in text or "brasserie" in text or "boutique" in text or "modern" in text or "4-star" in text:
#         return "$$"
#     if "$" in text or "affordable" in text or "cheap" in text or "budget" in text or "fast food" in text or "pizza" in text or "diner" in text or "casual" in text or "hostel" in text or "basic" in text or "value" in text:
#         return "$"
#     return None

def guess_price_range(text):
    text = text.lower()
    # Luxury indicators
    if (
        "$$$" in text or "fine dining" in text or "michelin" in text or
        "luxury" in text or "five-star" in text or "expensive" in text or
        "suite" in text or "penthouse" in text or "exclusive" in text or
        "high-end" in text or "gourmet" in text
    ):
        return "$$$"
    
    # Mid-range indicators
    if (
        "$$" in text or "mid-range" in text or "bistro" in text or
        "popular" in text or "moderate" in text or "brasserie" in text or
        "boutique" in text or "modern" in text or "4-star" in text or
        "casual dining" in text or "stylish" in text or "quality food" in text
    ):
        return "$$"
    
    # Cheap indicators
    if (
        "$" in text or "affordable" in text or "cheap" in text or
        "budget" in text or "fast food" in text or "pizza" in text or
        "diner" in text or "grab-and-go" in text or "street food" in text or
        "food court" in text or "local eatery" in text or "value for money" in text
    ):
        return "$"
    
    return None


# def categorize_by_price(results, is_restaurant=True):
#     grouped = defaultdict(list)
#     for res in results:
#         price = extract_price(res.get('content', '')) or guess_price_range(res.get('content', '')) or guess_price_range(res.get('title', ''))
#         if price == "$$$":
#             grouped["Luxury"].append(res)
#         elif price == "$$":
#             grouped["Mid-Range"].append(res)
#         elif price == "$":
#             grouped["Cheap"].append(res)
#         else:
#             grouped["Mid-Range"].append(res)  # Default if no info
#     return grouped

def categorize_by_price(results, is_restaurant=True):
    grouped = defaultdict(list)
    for res in results:
        title = res.get('title', '')
        content = res.get('content', '')

        # Try to extract from content first, then title
        price = (
            extract_price(content) or
            guess_price_range(content) or
            guess_price_range(title)
        )

        if price == "$$$":
            grouped["Luxury"].append(res)
        elif price == "$$":
            grouped["Mid-Range"].append(res)
        elif price == "$":
            grouped["Cheap"].append(res)
        else:
            grouped["Mid-Range"].append(res)  # fallback tier

    return grouped

def build_live_itinerary_prompt(destination: str, arrival_time: str, arrival_date: str, search_results: list, preferences: list[str], top_k: int) -> str:
    # Inject user preferences at the top
    pref_block = ""
    if preferences:
        pref_block = "**Traveler Preferences:**\n" + "\n".join(f"- {p}" for p in preferences) + "\n\n"

    prompt = f"""
You are a travel assistant AI helping a traveler plan their arrival-day experience.

{pref_block}The traveler is landing in **{destination}** on **{arrival_date}** at **{arrival_time}**.

You are given a set of **web search results** related to this destination. Use these results to generate your response.

---

### 🧠 Hybrid Logic:

- Categorize restaurants and hotels as Cheap, Mid-Range, and Luxury using price info or cues.
- Show up to {top_k} recommendations per tier.
- Show a clickable [Website Link] for each.
- Use internal knowledge (Fallback LLM) only if web results for a tier are missing.

---
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

    # Check if user wants to skip any section
    skip_restaurants = any("skip restaurant" in p.lower() for p in preferences)
    skip_hotels = any("skip hotel" in p.lower() for p in preferences)
    skip_rentals = any("skip rental" in p.lower() or "have a car" in p.lower() for p in preferences)

    # Restaurants - by tier
    if not skip_restaurants:
        prompt += "\n### 🍽️ Restaurants\n"
        if grouped['restaurant']:
            categorized = categorize_by_price(grouped['restaurant'], is_restaurant=True)
            for tier in ["Cheap", "Mid-Range", "Luxury"]:
                prompt += f"\n#### {tier}\n"
                items = categorized[tier]
                if items:
                    for result in items[:top_k]:
                        price_info = extract_price(result.get('content', '')) or guess_price_range(result.get('content', '')) or guess_price_range(result.get('title', ''))
                        prompt += (
                            f"- **{result.get('title', '')}**\n"
                            f"  {result.get('content', '')}\n"
                            f"  **Estimated Price:** {price_info if price_info else 'Not listed'}\n"
                        )
                        if result.get("url"):
                            prompt += f"  [Website Link]({result.get('url')})\n"
                else:
                    prompt += "_No options found in this tier._ (You may suggest known or plausible venues in this price tier using internal knowledge.)\n"
        else:
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
                        f"- **{name}**\n"
                        f"  _(No price info available)_\n"
                        f"  [Website Link]({google_link})\n"
                    )

    # Hotels - by tier
    if not skip_hotels:
        prompt += "\n### 🏨 Hotels\n"
        if grouped['hotel']:
            categorized = categorize_by_price(grouped['hotel'], is_restaurant=False)
            for tier in ["Cheap", "Mid-Range", "Luxury"]:
                prompt += f"\n#### {tier}\n"
                items = categorized[tier]
                if items:
                    for result in items[:top_k]:
                        price_info = extract_price(result.get('content', '')) or guess_price_range(result.get('content', '')) or guess_price_range(result.get('title', ''))
                        prompt += (
                            f"- **{result.get('title', '')}**\n"
                            f"  {result.get('content', '')}\n"
                            f"  **Estimated Price:** {price_info if price_info else 'Not listed'}\n"
                        )
                        if result.get("url"):
                            prompt += f"  [Website Link]({result.get('url')})\n"
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
                        f"- **{name}**\n"
                        f"  _(No price info available)_\n"
                        f"  [Website Link]({google_link})\n"
                    )

    # Rental Cars
    if not skip_rentals:
        prompt += "\n### 🚗 Rental Cars\n"
        if grouped['rental']:
            for result in grouped['rental'][:top_k]:
                prompt += (
                    f"- **{result.get('title', '')}**\n"
                    f"  {result.get('content', '')}\n"
                )
                if result.get("url"):
                    prompt += f"  [Website Link]({result.get('url')})\n"
        else:
            fallback_rentals = ["Hertz", "Avis", "Enterprise"]
            for name in fallback_rentals:
                google_link = f"https://www.google.com/search?q={destination.replace(' ', '+')}+car+rental"
                prompt += (
                    f"- **{name}**\n"
                    f"  [Website Link]({google_link})\n"
                )

    prompt += """

---

Now, using the **above search results first**, and your own knowledge *only when necessary*, generate a well-structured Markdown itinerary grouped by Cheap, Mid-Range, and Luxury for both restaurants and hotels. Do not hallucinate URLs or make up fake brands. Just show 'Website Link' for all URLs.
"""
    return prompt



def build_fallback_prompt(destination: str, arrival_time: str, arrival_date: str, preferences: list[str], top_k: int) -> str:
    pref_block = ""
    if preferences:
        pref_block = "**Traveler Preferences:**\n" + "\n".join(f"- {p}" for p in preferences) + "\n\n"

    # Skip flags
    skip_restaurants = any("skip restaurant" in p.lower() for p in preferences)
    skip_hotels = any("skip hotel" in p.lower() for p in preferences)
    skip_rentals = any("skip rental" in p.lower() or "have a car" in p.lower() for p in preferences)

    prompt = f"""
You are a travel assistant AI helping a traveler plan their arrival-day experience in **{destination}**, arriving at **{arrival_time}** on **{arrival_date}**.

{pref_block}There are no live web search results available, so you must use your own general knowledge and best judgment.
"""

    if not skip_restaurants:
        prompt += f"""

Your itinerary must be **grouped by price range (Cheap, Mid-Range, Luxury)** for both restaurants and hotels, with each entry using the same structured format as web-based results.

---

## 🍽️ Restaurants

**Please provide {top_k} recommendations in each of these categories:**
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
"""

    if not skip_hotels:
        prompt += f"""

---

## 🏨 Hotels

**Provide {top_k} recommendations in each of these categories:**
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
"""

    if not skip_rentals:
        prompt += f"""

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
"""

    prompt += """

---

**Important:**
- Make sure all recommendations are well-known or realistic for a major international city.
- Be concise but informative.
- Output must be **in clean Markdown**, with clear subheadings for each tier.
- Do NOT hallucinate details you are not confident about.
- Do NOT fabricate direct website URLs; always use a Google Search link for further info.
"""

    return prompt


def build_user_query_prompt(user_query, search_results, city=None, airport=None, arrival_time=None, arrival_date=None, chat_history=None):
    # Show context at the top if available

    history_note = ""
    if chat_history:
        history_note += "Earlier Conversation:\n"
        for i, chat in enumerate(chat_history[-5:], 1):
            history_note += f"{i}. Q: {chat['question']}\n   A: {chat['answer']}\n"
        history_note += "\nIf the user asks to 'elaborate' or 'what about that', use the relevant Q&A above.\n"
    context_note = ""
    if city or airport or arrival_time or arrival_date:
        context_note = "Traveler Context:\n"
        if city:
            context_note += f"- Destination city: {city}\n"
        if airport:
            context_note += f"- Arrival airport: {airport}\n"
        if arrival_time:
            context_note += f"- Arrival time: {arrival_time}\n"
        if arrival_date:
            context_note += f"- Arrival date: {arrival_date}\n"
        context_note += "\n(Use the above details as already known. Do NOT ask again.)\n"

    web_snippets = ""
    for r in search_results:
        link = f"[Website Link]({r.get('url','')})" if r.get('url') else ""
        web_snippets += f"\n- **{r.get('title', '')}**\n  {r.get('content', '')}\n  {link}\n"

    prompt = (
        f"You are a travel assistant AI. Use the context below and the web search results to answer the user as if you're a smart travel planner.\n"
        f"{context_note}"
        f"{history_note}"
        f"User Question:\n{user_query}\n\n"
        f"Recent Web Search Results:\n{web_snippets}\n"
        "Your response must be clear and relevant. Do not repeat what is already in the context."
    )
    return prompt
