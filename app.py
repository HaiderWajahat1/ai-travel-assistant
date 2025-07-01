from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from src.ocr_engine import extract_text_via_ocr_space
from src.nlp_extractor import extract_location_info
from src.gemma_client import call_gemma
from config.prompts import build_detailed_itinerary_prompt, build_live_itinerary_prompt
from src.searx_client import search_searx


app = FastAPI()

class TextInput(BaseModel):
    raw_text: str
    
@app.post("/extract-details")
def extract_info_from_text(input: TextInput):
    try:
        result = extract_location_info(input.raw_text)
        return JSONResponse(content={"structured_info": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    text = await extract_text_via_ocr_space(file)
    if text:
        return JSONResponse(content={"extracted_text": text})
    raise HTTPException(status_code=500, detail="OCR failed.")


@app.post("/extract-structured-info")
async def extract_structured_info(file: UploadFile = File(...)):
    try:
        # Step 1: OCR
        text = await extract_text_via_ocr_space(file)
        if not text:
            raise HTTPException(status_code=500, detail="OCR failed to extract any text")

        # Step 2: NLP extraction
        structured_data = extract_location_info(text)
        return JSONResponse(content={
            "structured_info": structured_data
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
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
#         arrival_time = structured_data.get("arrival_time", "TBD")
#         arrival_date = structured_data.get("arrival_date", "TBD")

#         # Run SearxNG search for live POIs/restaurants
#         live_results = search_searx(f"Top restaurants and hotels in {destination}")

#         if not destination:
#             raise HTTPException(status_code=400, detail="Destination not found in extracted data")

#         # Step 3: POIs and Recommendations from Gemma
#         prompt = build_live_itinerary_prompt(destination, arrival_time, arrival_date,live_results)
#         # prompt = build_detailed_itinerary_prompt(destination, arrival_time, arrival_date)
#         gemma_output = call_gemma(prompt).get("result", "No response.")

#         return PlainTextResponse(content=gemma_output)
    

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/display-itinerary")
async def display_itinerary(file: UploadFile = File(...)):
    try:
        # Step 1: OCR
        text = await extract_text_via_ocr_space(file)
        if not text:
            raise HTTPException(status_code=500, detail="OCR failed")

        # Step 2: NLP extraction
        structured_data = extract_location_info(text)

        destination = structured_data.get("destination")
        arrival_time = structured_data.get("arrival_time", "TBD")
        arrival_date = structured_data.get("arrival_date", "TBD")

        if not destination:
            raise HTTPException(status_code=400, detail="Destination not found in structured data")

        # ✅ Step 3: Call SearxNG for live data
        live_results = search_searx(f"Top restaurants, hotels, rental cars in {destination}")

        # Step 4: Build Gemma prompt using those live results
        prompt = build_live_itinerary_prompt(destination, arrival_date, arrival_time, live_results)

        # Step 5: Query Gemma
        result = call_gemma(prompt)
        text = result.get("result") or result.get("output", "No response from Gemma.")
        return JSONResponse(content={"itinerary": text})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    

@app.get("/web-search-itinerary")
def web_search_itinerary(destination: str):
    results = search_searx(f"Top restaurants and hotels in {destination}")
    prompt = build_live_itinerary_prompt(destination, "TBD", "TBD", results)
    gemma_response = call_gemma(prompt).get("result", "Gemma failed.")
    return {"response": gemma_response}
