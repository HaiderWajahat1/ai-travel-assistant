from fastapi import FastAPI, UploadFile, File, HTTPException
from src.ocr_engine import extract_text_from_file
from pydantic import BaseModel
from src.nlp_extractor import extract_location_info

app = FastAPI()


class TextInput(BaseModel):
    raw_text: str

@app.post("/extract-details")
def extract_info_from_text(input: TextInput):
    result = extract_location_info(input.raw_text)
    return {"structured_info": result}


@app.post("/ocr")
async def ocr_extract(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        text = extract_text_from_file(file_bytes)
        return {"extracted_text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        raw_text = extract_text_from_file(file_bytes)
        structured = extract_location_info(raw_text)
        return {
            "extracted_text": raw_text,
            "structured_info": structured
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))