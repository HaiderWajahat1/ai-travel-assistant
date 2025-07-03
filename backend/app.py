from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.ocr_engine import extract_text_via_ocr_space
from src.nlp_extractor import extract_location_info
from src.gemma_client import call_gemma
from config.prompts import build_fallback_prompt, build_live_itinerary_prompt
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


class CustomItineraryRequest(BaseModel):
    base_prompt: str
    user_input: str
    
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
    
@app.post("/display-itinerary")
async def display_itinerary(file: UploadFile = File(...)):
    try:
        # Step 1: OCR
        text = await extract_text_via_ocr_space(file)
        if not text:
            raise HTTPException(status_code=500, detail="OCR failed to extract text")

        # Step 2: NLP Extraction
        structured_data = extract_location_info(text)
        destination = structured_data.get("destination")
        arrival_time = structured_data.get("arrival_time", "TBD")
        arrival_date = structured_data.get("arrival_date", "TBD")

        if not destination:
            raise HTTPException(status_code=400, detail="Destination not found in extracted data")

        # Step 3: Web search
        restaurants = search_searx(f"best restaurants in {destination}", tag="restaurant", max_results=6)
        hotels = search_searx(f"best hotels in {destination}", tag="hotel", max_results=6)
        rentals = search_searx(f"car rentals in {destination}", tag="rental", max_results=4)

        search_results = restaurants + hotels + rentals

        # Step 4: Decide if fallback is needed
        result_titles = [r.get("title", "").lower() for r in search_results]
        has_results = any("restaurant" in t or "hotel" in t or "car" in t for t in result_titles)

        # Step 5: Prompt building
        if has_results:
            prompt = build_live_itinerary_prompt(destination, arrival_time, arrival_date, search_results)
        else:
            prompt = build_fallback_prompt(destination, arrival_time, arrival_date)

        # Step 6: LLM Call
        gemma_output = call_gemma(prompt)

        return {"itinerary": gemma_output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


# --- NEW: CUSTOM ITINERARY ENDPOINT ---
@app.post("/custom-itinerary")
def custom_itinerary(req: CustomItineraryRequest):
    """
    Accepts a base itinerary prompt and user's extra instruction, combines, and calls LLM.
    """
    final_prompt = req.base_prompt.strip()
    if req.user_input:
        final_prompt += f"\nUser customization request: {req.user_input.strip()}"

    # Call LLM (Gemma or whatever you're using)
    gemma_output = call_gemma(final_prompt)

    return {"itinerary": gemma_output}
    


