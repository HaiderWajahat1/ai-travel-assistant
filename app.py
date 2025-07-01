from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.ocr_engine import extract_text_via_ocr_space
from src.nlp_extractor import extract_location_info

app = FastAPI()

class TextInput(BaseModel):
    raw_text: str

@app.post("/ocr")
async def ocr_extract(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        cleaned_text = extract_text_from_file(file_bytes)
        return {"extracted_text": cleaned_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        text = extract_text_from_file(file_bytes)
        structured = extract_location_info(text)
        return {
            "extracted_text": text,
            "structured_info": structured
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

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
