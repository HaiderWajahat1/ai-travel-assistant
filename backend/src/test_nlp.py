from src.nlp_extractor import extract_location_info

ocr_text = """
BOARDING PASS
Passenger Name
JOHN SMITH
From
PARIS
To
RIO DE JANEIRO
Date
09JUN
Flight F 0575
08:40
"""

result = extract_location_info(ocr_text)
print(result)
