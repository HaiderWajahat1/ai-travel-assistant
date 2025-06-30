import easyocr
import numpy as np
import cv2
from PIL import Image
from io import BytesIO

reader = easyocr.Reader(['en'])



def extract_text_from_file(file_bytes: bytes) -> str:
    image = Image.open(BytesIO(file_bytes)).convert("RGB")
    np_img = np.array(image)
    result = reader.readtext(np_img, detail=0)
    return "\n".join(result)
