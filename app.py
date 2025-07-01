from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.ocr_engine import extract_text_via_ocr_space
from src.nlp_extractor import extract_location_info

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
