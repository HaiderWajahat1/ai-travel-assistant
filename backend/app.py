from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.ocr_engine import extract_text_via_ocr_space
from src.nlp_extractor import extract_location_info
from src.gemma_client import call_gemma
from config.prompts import build_fallback_prompt, build_live_itinerary_prompt, build_user_query_prompt
from src.searx_client import search_searx
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local dev, restrict in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextInput(BaseModel):
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

@app.post("/extract-ocr-text")
async def extract_ocr_text_endpoint(file: UploadFile = File(...)):
    try:
        text = await extract_text_via_ocr_space(file)
        if not text:
            raise HTTPException(status_code=500, detail="OCR failed to extract text")
        return {"ocr_text": text}
    except Exception as e:
        print("🚨 OCR endpoint error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OCR extraction error: {str(e)}")


@app.post("/parse-ocr-text")
async def parse_ocr_text_endpoint(data: TextInput):
    """
    Accept raw OCR text and return structured fields via NLP (Gemma).
    """
    try:
        result = extract_location_info(data.raw_text)
        return {"parsed_info": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLP parsing error: {str(e)}")


@app.post("/display-itinerary")
async def display_itinerary(
    file: UploadFile = File(...),
    preferences: str = Form(""),
    top_k: int = Form(3)
):
    try:
        user_prefs = [p.strip() for p in preferences.split(",") if p.strip()]

        exclusion_flags = {
            "skip_hotels": False,
            "skip_rentals": False,
            "skip_restaurants": False
        }

        for pref in user_prefs:
            lowered = pref.lower()
            if "have a car" in lowered or ("rental" in lowered and "not needed" in lowered):
                exclusion_flags["skip_rentals"] = True
            if "have accommodation" in lowered or "hotel is booked" in lowered or "no hotel" in lowered:
                exclusion_flags["skip_hotels"] = True
            if "no food" in lowered or "don't want restaurants" in lowered:
                exclusion_flags["skip_restaurants"] = True

        # Step 1: OCR
        text = await extract_text_via_ocr_space(file)
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

        # if not exclusion_flags["skip_restaurants"]:
        #     # Mid/Luxury
        #     search_results += search_searx(f"best restaurants in {destination}", tag="restaurant", max_results=5)
        #     # Cheap-specific
        #     search_results += search_searx(f"cheap restaurants in {destination}", tag="restaurant", max_results=5)

        # if not exclusion_flags["skip_hotels"]:
        #     # Mid/Luxury
        #     search_results += search_searx(f"best hotels in {destination}", tag="hotel", max_results=5)
        #     # Cheap-specific
        #     search_results += search_searx(f"budget hotels in {destination}", tag="hotel", max_results=5)

        # if not exclusion_flags["skip_rentals"]:
        #     search_results += search_searx(f"car rentals in {destination}", tag="rental", max_results=5)

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


        # Optional: Add simple category tagging for cheap results
        for item in search_results:
            title = item.get("title", "").lower()
            if "cheap" in title or "budget" in title or "affordable" in title:
                item["category_hint"] = "cheap"


        # ✅ Updated logic: more robust result check
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
        return {"itinerary": gemma_output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/ask")
def ask_endpoint(req: AskRequest):
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
