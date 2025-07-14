import os
import re
import yaml
import httpx
import unicodedata
from fastapi import UploadFile
from typing import Optional
from dotenv import load_dotenv
from src.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Load environment variables and YAML config
load_dotenv()
with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

# Keys
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")
OCR_SPACE_API_URL = config["OCR_SPACE_API_URL"]
AZURE_CV_ENDPOINT = config["AZURE_CV_ENDPOINT"]
AZURE_CV_API_KEY = os.getenv("AZURE_CV_API_KEY")


def clean_azure_ocr(text: str) -> str:
    """
    Cleans and normalizes OCR text extracted via Azure.

    Args:
        text (str): Raw OCR text.

    Returns:
        str: Cleaned and normalized text.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = text.replace("LONDIB", "LONDON").replace("ISLAADA", "ISLAMABAD")
    text = text.replace("DUBAN", "DUBAI")
    return text.strip()


async def extract_via_ocr_space(file: UploadFile) -> Optional[str]:
    """
    Extracts text from an image using the OCR.Space API.

    Args:
        file (UploadFile): The uploaded image file.

    Returns:
        Optional[str]: The extracted text, or None if extraction fails.
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
            logger.info("OCR.Space Output:\n%s", parsed[0]["ParsedText"])
            return parsed[0]["ParsedText"].strip()
        return None

    except Exception as e:
        logger.error("OCR.Space error: %s", repr(e))
        return None


async def extract_via_azure_ocr(file: UploadFile) -> Optional[str]:
    """
    Extracts text from an image using the Azure Computer Vision OCR API.

    Args:
        file (UploadFile): The uploaded image file.

    Returns:
        Optional[str]: The cleaned extracted text, or None if extraction fails.
    """
    if not AZURE_CV_API_KEY or not AZURE_CV_ENDPOINT:
        logger.warning("Missing Azure OCR key or endpoint in .env")
        return None

    try:
        image_data = await file.read()
        ocr_url = AZURE_CV_ENDPOINT.rstrip("/") + "/vision/v3.2/ocr?language=unk&detectOrientation=true"
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_CV_API_KEY,
            "Content-Type": "application/octet-stream"
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = await client.post(ocr_url, headers=headers, content=image_data)

        response.raise_for_status()
        result = response.json()

        lines = []
        for region in result.get("regions", []):
            for line in region.get("lines", []):
                line_text = " ".join([word["text"] for word in line["words"]])
                lines.append(line_text)

        full_text = "\n".join(lines).strip()
        cleaned = clean_azure_ocr(full_text)
        logger.info("Azure OCR Output:\n%s", cleaned)
        return cleaned if cleaned else None

    except httpx.HTTPStatusError as e:
        logger.error("HTTP error from Azure OCR: %s %s", e.response.status_code, e.response.text)
    except Exception as e:
        logger.error("Unhandled Azure OCR exception: %s", repr(e))

    return None


async def extract_text_via_ocr(file: UploadFile) -> Optional[str]:
    """
    Dynamically selects the OCR engine based on availability of the OCR.Space API key.
    Uses OCR.Space if key is provided, otherwise falls back to Azure OCR.

    Args:
        file (UploadFile): The uploaded image file.

    Returns:
        Optional[str]: The final extracted and cleaned text, or None if both methods fail.
    """
    if OCR_SPACE_API_KEY not in [None, "", "null", "None"]:
        logger.info("Using OCR.Space")
        return await extract_via_ocr_space(file)
    else:
        logger.info("Falling back to Azure OCR")
        return await extract_via_azure_ocr(file)
