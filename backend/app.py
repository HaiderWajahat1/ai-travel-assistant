# Third-party
from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Local modules
from src.ocr_engine import extract_text_via_ocr
from src.nlp_extractor import extract_location_info
from src.gemma_client import call_gemma, extract_keywords_from_preferences
from config.prompts import (
    build_fallback_prompt,
    build_live_itinerary_prompt,
    build_user_query_prompt
)
from src.searx_client import search_searx


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local dev, restrict in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextInput(BaseModel):
    """Input model for parsed OCR text."""
    raw_text: str
    top_k: int

class AskRequest(BaseModel):
    user_query: str

last_context = {
    "city": None,
    "airport": None,
    "arrival_time": None,
    "arrival_date": None
}

chat_history = []

@app.post("/display-itinerary")
async def display_itinerary(
    file: UploadFile = File(...),
    preferences: str = Form(""),
    top_k: int = Form(3)
):
    """
    Generates a personalized travel itinerary based on the uploaded ticket and user preferences.

    Process Flow:
    - Performs OCR on the uploaded image to extract text.
    - Uses an LLM to extract structured travel information (e.g., destination, airport, arrival time/date).
    - Applies preference-based filters (e.g., skip hotels, rentals, food).
    - Performs live web searches for relevant POIs using extracted keywords and destination.
    - Builds a prompt and generates an itinerary using Gemma LLM.

    Args:
        file (UploadFile): Image file of the boarding pass or travel ticket.
        preferences (str): Comma-separated freeform preferences (e.g., "hiking, no food, own car").
        top_k (int): Number of suggestions to include per category (used for prompt generation).

    Returns:
        dict: A response containing:
            - `itinerary` (str): Generated text-based itinerary.
            - `city` (str): Destination city.
            - `origin` (str): Departure city.
            - `airport` (str): Destination airport name or code.
            - `arrival_time` (str): Parsed arrival time (if available).
    """
    try:
        user_prefs = [p.strip() for p in preferences.split(",") if p.strip()]

        exclusion_flags = {
            "skip_rentals": False,
            "skip_hotels": False,
            "skip_restaurants": False
        }

        for pref in user_prefs:
            lowered = pref.lower()
            # Rentals - Detect if user has a car or doesn't need rental
            if any(x in lowered for x in [
                "have a car","has a car", "own car", "my car", "rented a car", "already have car", 
                "don't need rental", "rental not needed", "rental sorted", "car sorted", 
                "bringing my own car", "using personal car", "self-driving", "car arranged"
            ]):
                exclusion_flags["skip_rentals"] = True

            # Hotels - Detect if user has accommodation
            if any(x in lowered for x in [
                "have accommodation", "hotel is booked", "already booked hotel", 
                "no hotel", "don't need hotel", "staying at", "staying with", 
                "place to stay", "friend's place", "airbnb", "lodging sorted", 
                "arranged stay", "accommodation sorted", "sleeping at relative's", 
                "guesthouse booked", "residence arranged", "living with someone"
            ]):
                exclusion_flags["skip_hotels"] = True

            # Restaurants - Detect if user doesn't want food suggestions
            if any(x in lowered for x in [
                "no food", "skip meals", "don't want restaurants", "bring my own food", 
                "meals are sorted", "eating at hotel", "already have food", "eating with family", 
                "self-catering", "meal plan included", "staying with someone who'll feed me", 
                "homemade meals", "not interested in dining out", "food taken care of", 
                "will cook", "will order in", "on a diet", "not eating out"
            ]):
                exclusion_flags["skip_restaurants"] = True


        # Step 1: OCR
        text = await extract_text_via_ocr(file)
        if not text:
            raise HTTPException(status_code=500, detail="OCR failed to extract text")

        # Step 2: NLP Extraction
        structured_data = extract_location_info(text)
        destination = structured_data.get("destination")
        airport = structured_data.get("airport_name") or structured_data.get("airport_code")
        arrival_time = structured_data.get("arrival_time", "TBD")
        arrival_date = structured_data.get("arrival_date", "TBD")


        if destination:
            last_context["city"] = destination
        if airport:
            last_context["airport"] = airport
        if arrival_time:
            last_context["arrival_time"] = arrival_time
        if arrival_date:
            last_context["arrival_date"] = arrival_date

        if not destination:
            raise HTTPException(status_code=400, detail="Destination not found in extracted data")

        # Step 3: Web search
        search_results = []
        multiplier = 2.5
        search_k = int(top_k * multiplier)

        if not exclusion_flags["skip_restaurants"]:
            search_results += search_searx(f"best restaurants in {destination}", tag="restaurant", max_results=search_k)
            search_results += search_searx(f"cheap restaurants in {destination}", tag="restaurant", max_results=search_k)

        if not exclusion_flags["skip_hotels"]:
            search_results += search_searx(f"best hotels in {destination}", tag="hotel", max_results=search_k)
            search_results += search_searx(f"budget hotels in {destination}", tag="hotel", max_results=search_k)

        if not exclusion_flags["skip_rentals"]:
            search_results += search_searx(f"car rentals in {destination}", tag="rental", max_results=search_k)

        # Additional dynamic searches from LLM-extracted preferences
        dynamic_keywords = extract_keywords_from_preferences(user_prefs)
        for keyword in dynamic_keywords:
            query = f"{keyword} in {destination}"
            search_results += search_searx(query, max_results=search_k)
            for r in search_results[-search_k:]:
                r["category"] = "general"


        # Add simple category tagging for cheap results
        for item in search_results:
            title = item.get("title", "").lower()
            if "cheap" in title or "budget" in title or "affordable" in title:
                item["category_hint"] = "cheap"

        has_results = len(search_results) > 0

        if has_results:
            if exclusion_flags["skip_rentals"]:
                user_prefs.append("Skip car rental suggestions — traveler already has a vehicle.")
            if exclusion_flags["skip_hotels"]:
                user_prefs.append("Skip hotel suggestions — traveler already has accommodation.")
            if exclusion_flags["skip_restaurants"]:
                user_prefs.append("Skip restaurant suggestions.")

            prompt = build_live_itinerary_prompt(destination, arrival_time, arrival_date, search_results, user_prefs, top_k)
        else:
            prompt = build_fallback_prompt(destination, arrival_time, arrival_date, user_prefs, top_k)

        gemma_output = call_gemma(prompt)
        return {
            "itinerary": gemma_output,
            "city": destination,
            "origin": structured_data.get("origin"),
            "airport": airport,
            "arrival_time": arrival_time
        }


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/ask")
def ask_endpoint(req: AskRequest):
    """
    Handles user Q&A based on previous travel context and live web search results.

    - Uses previous itinerary context (destination, arrival time, airport) to enhance the user's query.
    - Performs a live search using SearxNG.
    - Sends the query, search results, and chat history to Gemma for reasoning and response.
    - Stores chat history and summarizes old messages if more than 5 interactions.

    Args:
        req (AskRequest): A JSON body with a single field: `user_query` (str).

    Returns:
        dict: A response containing:
            - `answer` (str): Generated answer from Gemma.
            - `history` (list): The last 5 Q&A interactions.
            - `summary` (str): Summary of earlier interactions (if any).
    """
    user_query = req.user_query
    city = last_context.get("city")
    airport = last_context.get("airport")
    arrival_time = last_context.get("arrival_time")
    arrival_date = last_context.get("arrival_date")

    enhanced_query = user_query
    if city and city.lower() not in user_query.lower():
        enhanced_query += f" in {city}"
    if airport and airport.lower() not in user_query.lower():
        enhanced_query += f" near {airport}"

    search_results = search_searx(enhanced_query, max_results=6)

    # Use existing chat history if present
    prompt = build_user_query_prompt(
        user_query,
        search_results,
        city=city,
        airport=airport,
        arrival_time=arrival_time,
        arrival_date=arrival_date,
        chat_history=chat_history
    )

    answer = call_gemma(prompt)

    # Extract answer text
    if isinstance(answer, dict):
        answer_text = answer.get("output", "")
    else:
        answer_text = answer

    # Store chat in memory
    chat_history.append({"question": user_query, "answer": answer_text})

    # Keep only the latest 5, summarize old ones
    summary_blob = ""
    if len(chat_history) > 5:
        older = chat_history[:-5]
        chat_history[:] = chat_history[-5:]

        summary_blob = "SUMMARY OF EARLIER CONVERSATION:\n"
        for i, chat in enumerate(older, 1):
            summary_blob += f"{i}. Q: {chat['question']}\n   A: {chat['answer']}\n"

    return {
        "answer": answer_text,
        "history": chat_history,
        "summary": summary_blob
    }
