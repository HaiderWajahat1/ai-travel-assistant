import httpx
import cv2
import numpy as np
import tempfile
from fastapi import UploadFile
from typing import Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
OCR_SPACE_API_URL = "https://api.ocr.space/parse/image"
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")


def auto_crop_document(image_bytes: bytes) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    orig = image.copy()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            cropped = orig[y:y+h, x:x+w]
            break
    else:
        cropped = orig  # fallback to original if no document-like contour is found

    # Debug image output
    cv2.imwrite("debug_cropped.jpg", cropped)

    _, cropped_bytes = cv2.imencode('.jpg', cropped)
    return cropped_bytes.tobytes()


async def extract_text_via_ocr_space(file: UploadFile) -> Optional[str]:
    try:
        file_bytes = await file.read()
        cropped_bytes = auto_crop_document(file_bytes)

        text = await send_to_ocr_space(cropped_bytes, file.filename)
        if not text:
            print("❌ Cropped OCR failed — trying without cropping...")
            text = await send_to_ocr_space(file_bytes, file.filename)

        return text
    except Exception as e:
        print("Unhandled OCR exception:", repr(e))
        return None


async def send_to_ocr_space(image_bytes: bytes, filename: str) -> Optional[str]:
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp:
            temp.write(image_bytes)
            temp.flush()
            temp_path = temp.name

        with open(temp_path, "rb") as f:
            files = {
                "file": (filename, f, "image/jpeg")
            }
            data = {
                "language": "eng",
                "isOverlayRequired": False,
                "OCREngine": 2
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

        response.raise_for_status()
        result = response.json()

        print("📦 Full OCR API response:", result)  # Debug line

        parsed = result.get("ParsedResults", [])
        if parsed and isinstance(parsed, list):
            text = parsed[0].get("ParsedText", "")
            if text.strip():
                return text.strip()
            else:
                print("ParsedResults exists but text is empty:", parsed[0])
        else:
            print("OCR API returned no ParsedResults or unexpected format:", result)

    except httpx.HTTPStatusError as e:
        print("HTTP error from OCR API:", e.response.status_code, e.response.text)
    except Exception as e:
        print("Exception while sending to OCR.Space:", repr(e))

    return None
