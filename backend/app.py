from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.ocr_engine import extract_text_via_ocr_space
from src.nlp_extractor import extract_location_info
from src.gemma_client import call_gemma
from config.prompts import build_fallback_prompt, build_live_itinerary_prompt, build_user_query_prompt
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
    raw_text: str


class AskRequest(BaseModel):
    user_query: str

last_context = {
    "city": None,
    "airport": None
}

    
# @app.post("/extract-details")
# def extract_info_from_text(input: TextInput):
#     try:
#         result = extract_location_info(input.raw_text)
#         return JSONResponse(content={"structured_info": result})
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/extract-text")
# async def extract_text(file: UploadFile = File(...)):
#     text = await extract_text_via_ocr_space(file)
#     if text:
#         return JSONResponse(content={"extracted_text": text})
#     raise HTTPException(status_code=500, detail="OCR failed.")


# @app.post("/extract-structured-info")
# async def extract_structured_info(file: UploadFile = File(...)):
#     try:
#         # Step 1: OCR
#         text = await extract_text_via_ocr_space(file)
#         if not text:
#             raise HTTPException(status_code=500, detail="OCR failed to extract any text")

#         # Step 2: NLP extraction
#         structured_data = extract_location_info(text)
#         return JSONResponse(content={
#             "structured_info": structured_data
#         })

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# good stuff
# @app.post("/display-itinerary")
# async def display_itinerary(file: UploadFile = File(...)):
#     try:
#         # Step 1: OCR
#         text = await extract_text_via_ocr_space(file)
#         if not text:
#             raise HTTPException(status_code=500, detail="OCR failed to extract text")

#         # Step 2: NLP Extraction
#         structured_data = extract_location_info(text)
#         destination = structured_data.get("destination")
#         airport = structured_data.get("airport_name") or structured_data.get("airport_code")  # Use both if possible
#         arrival_time = structured_data.get("arrival_time", "TBD")
#         arrival_date = structured_data.get("arrival_date", "TBD")
#         if destination:
#             last_context["city"] = destination
#         if airport:
#             last_context["airport"] = airport
#         if not destination:
#             raise HTTPException(status_code=400, detail="Destination not found in extracted data")

#         # Step 3: Web search
#         restaurants = search_searx(f"best restaurants in {destination}", tag="restaurant", max_results=6)
#         hotels = search_searx(f"best hotels in {destination}", tag="hotel", max_results=6)
#         rentals = search_searx(f"car rentals in {destination}", tag="rental", max_results=4)

#         search_results = restaurants + hotels + rentals

#         # Step 4: Decide if fallback is needed
#         result_titles = [r.get("title", "").lower() for r in search_results]
#         has_results = any("restaurant" in t or "hotel" in t or "car" in t for t in result_titles)

#         # Step 5: Prompt building
#         if has_results:
#             prompt = build_live_itinerary_prompt(destination, arrival_time, arrival_date, search_results)
#         else:
#             prompt = build_fallback_prompt(destination, arrival_time, arrival_date)

#         # Step 6: LLM Call
#         gemma_output = call_gemma(prompt)

#         return {"itinerary": gemma_output}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("/display-itinerary")
async def display_itinerary(
    file: UploadFile = File(...),
    preferences: str = Form(""),
    top_k: int = Form(3)
):
    try:
        user_prefs = [p.strip() for p in preferences.split(",") if p.strip()]

        # Flags to skip sections
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
        if not destination:
            raise HTTPException(status_code=400, detail="Destination not found in extracted data")

        # Step 3: Web search
        search_results = []
        if not exclusion_flags["skip_restaurants"]:
            search_results += search_searx(f"best restaurants in {destination}", tag="restaurant", max_results=6)
        if not exclusion_flags["skip_hotels"]:
            search_results += search_searx(f"best hotels in {destination}", tag="hotel", max_results=6)
        if not exclusion_flags["skip_rentals"]:
            search_results += search_searx(f"car rentals in {destination}", tag="rental", max_results=4)

        result_titles = [r.get("title", "").lower() for r in search_results]
        has_results = any("restaurant" in t or "hotel" in t or "car" in t for t in result_titles)

        # Step 4: Prompt
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
    


# --- NEW: search bar ENDPOINT ---
@app.post("/ask")
def ask_endpoint(req: AskRequest):
    user_query = req.user_query
    city = last_context.get("city")
    airport = last_context.get("airport")

    # Smartly add context if not in user query
    enhanced_query = user_query
    if city and city.lower() not in user_query.lower():
        enhanced_query += f" in {city}"
    if airport and airport.lower() not in user_query.lower():
        enhanced_query += f" near {airport}"

    # Web search uses the enhanced query
    search_results = search_searx(enhanced_query, max_results=6)

    # Pass city/airport context to the prompt builder
    prompt = build_user_query_prompt(user_query, search_results, city=city, airport=airport)

    answer = call_gemma(prompt)
    return {"answer": answer}