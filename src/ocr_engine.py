import httpx
from fastapi import UploadFile
from typing import Optional

OCR_SPACE_API_URL = "https://api.ocr.space/parse/image"
OCR_SPACE_API_KEY = "K84499695988957"

async def extract_text_via_ocr_space(file: UploadFile) -> Optional[str]:
    try:
        file_bytes = await file.read()
        files = {
            "file": (file.filename, file_bytes, file.content_type)
        }
        data = {
            "language": "eng",
            "isOverlayRequired": False
        }
        headers = {
            "apikey": OCR_SPACE_API_KEY
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                OCR_SPACE_API_URL,
                data=data,
                files=files,
                headers=headers
            )

        # 💥 Check for HTTP errors
        response.raise_for_status()

        result = response.json()
        parsed = result.get("ParsedResults", [])
        if parsed:
            return parsed[0].get("ParsedText", "").strip()
        else:
            print("OCR API returned no ParsedResults:", result)
            return None
    except httpx.HTTPStatusError as e:
        print("HTTP error from OCR API:", e.response.status_code, e.response.text)
    except Exception as e:
        print("Unhandled OCR exception:", repr(e))
    return None
