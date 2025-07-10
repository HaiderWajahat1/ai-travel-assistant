import httpx
from fastapi import UploadFile
from typing import Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
OCR_SPACE_API_URL = "https://api.ocr.space/parse/image"
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")


async def extract_text_via_ocr_space(file: UploadFile) -> Optional[str]:
    """
    Sends an image file to OCR.Space API and returns extracted text if successful.
    """
    try:
        image_data = await file.read()
        files = {"file": (file.filename, image_data, "image/jpeg")}
        data = {"language": "eng", "isOverlayRequired": False, "OCREngine": 2}
        headers = {"apikey": OCR_SPACE_API_KEY}

        async with httpx.AsyncClient() as client:
            response = await client.post(OCR_SPACE_API_URL, data=data, files=files, headers=headers)
        response.raise_for_status()

        result = response.json()
        parsed = result.get("ParsedResults", [])
        if parsed and parsed[0].get("ParsedText", "").strip():
            return parsed[0]["ParsedText"].strip()
        return None

    except Exception as e:
        print("OCR.Space error:", repr(e))
        return None


# Uncomment the following code if you want to use Azure OCR instead of OCR.Space

# import os
# import re
# import unicodedata
# from fastapi import UploadFile
# from typing import Optional
# from dotenv import load_dotenv
# import httpx

# load_dotenv()

# AZURE_CV_API_KEY = os.getenv("AZURE_CV_API_KEY")
# AZURE_CV_ENDPOINT = os.getenv("AZURE_CV_ENDPOINT")

# def clean_azure_ocr(text: str) -> str:
#     # Normalize unicode (e.g., Å → A)
#     text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

#     # Replace non-ASCII junk
#     text = re.sub(r"[^\x00-\x7F]+", "", text)

#     # Normalize line breaks
#     text = re.sub(r"\n{2,}", "\n", text)

#     # Optional: fix common OCR misreads
#     text = text.replace("LONDIB", "LONDON").replace("ISLAADA", "ISLAMABAD")
#     text = text.replace("DUBAN", "DUBAI")

#     return text.strip()

# async def extract_text_via_ocr_space(file: UploadFile) -> Optional[str]:
#     if not AZURE_CV_API_KEY or not AZURE_CV_ENDPOINT:
#         print("Missing Azure OCR key or endpoint in .env")
#         return None

#     try:
#         image_data = await file.read()

#         ocr_url = AZURE_CV_ENDPOINT.rstrip("/") + "/vision/v3.2/ocr?language=unk&detectOrientation=true"

#         headers = {
#             "Ocp-Apim-Subscription-Key": AZURE_CV_API_KEY,
#             "Content-Type": "application/octet-stream"
#         }

#         async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
#             response = await client.post(ocr_url, headers=headers, content=image_data)

#         response.raise_for_status()
#         result = response.json()

#         # Extract raw lines
#         lines = []
#         for region in result.get("regions", []):
#             for line in region.get("lines", []):
#                 line_text = " ".join([word["text"] for word in line["words"]])
#                 lines.append(line_text)

#         full_text = "\n".join(lines).strip()
#         cleaned = clean_azure_ocr(full_text)

#         print("🧾 Azure OCR Output:\n", cleaned)
#         return cleaned if cleaned else None

#     except httpx.HTTPStatusError as e:
#         print("HTTP error from Azure OCR:", e.response.status_code, e.response.text)
#     except Exception as e:
#         print("Unhandled Azure OCR exception:", repr(e))

#     return None
