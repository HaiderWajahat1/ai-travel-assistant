from pydantic import BaseModel

class TripRequest(BaseModel):
    image_base64: str

class TripResponse(BaseModel):
    itinerary: str
