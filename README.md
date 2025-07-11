# AI Travel Planner

An intelligent travel assistant that takes a simple boarding pass or ticket image and turns it into a personalized travel itinerary — complete with live recommendations for restaurants, hotels, rentals, and local attractions. Users can also ask follow-up questions like “Where to get a SIM card?” or “What’s the weather like?” — and receive contextual answers instantly.

---

![Demo](frontend/demo.gif)

---

## 🔍 Features

- OCR-based ticket scanning and location extraction  
- LLM-powered parsing of origin, destination, airport, arrival time/date  
- Preference-aware itinerary generation (e.g. "no food", "have a car")  
- Live web search via SearxNG for POIs, restaurants, hotels, rentals  
- Route map generation with Folium and OpenStreetMap  
- Clean markdown output with price tiers and links  
- Interactive Q&A chatbot for post-itinerary queries  

---

## ⚙️ Tech Stack

| Component   | Technology Used                       |
|------------|----------------------------------------|
| Backend     | FastAPI, httpx, OCR.Space, Geopy, Gemma LLM |
| Frontend    | Streamlit, Folium                     |
| AI/NLP      | Google Gemma 3 27B API                |
| Search      | Locally hosted SearxNG instance       |
| OCR         | OCR.Space API                         |
| Geolocation | Geopy (Nominatim)                     |

---

## 🛠️ Setup

### 📄 Environment Variables

Create a `.env` file inside your `/backend` directory with the following keys:

```env
OCR_SPACE_API_KEY=your_ocr_key
GEMMA_API_KEY=your_gemma_key
SEARX_URL=http://localhost:4000
````

---

### ▶️ Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

---

### 💻 Frontend Setup

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

---

## 🧭 How It Works

1. User uploads a travel ticket (JPG/PNG)
2. OCR extracts raw text (e.g. flight number, airport, dates)
3. LLM parses and corrects this into structured fields
4. Preferences are checked (e.g. "skip hotel", "already have food")
5. Relevant live data is pulled using SearxNG
6. LLM formats everything into a beautiful, markdown itinerary
7. User can optionally chat with the planner about their trip

---

## 📂 Project Structure

```txt
.
├── backend/
│   ├── app.py              # FastAPI routes
│   ├── src/
│   │   ├── ocr_engine.py
│   │   ├── gemma_client.py
│   │   ├── searx_client.py
│   │   └── city_corrector.py
│   └── config/prompts.py   # Prompt engineering layer
├── frontend/
│   ├── app.py              # Streamlit frontend
│   └── route_map.py        # Folium map rendering
├── data/
│   └── worldcities.csv     # For fuzzy city correction
```

---

## 🧪 API Endpoints

* `POST /display-itinerary`
  Accepts file + preferences, returns structured markdown itinerary

* `POST /ask`
  Accepts a question (e.g. “What’s the weather like?”), returns LLM answer

Test with:

```bash
curl -X POST http://localhost:8000/display-itinerary ...
```


## 🧼 Dev Notes

* Chat history is stored in session state
* Uses Folium with colored markers and route lines
* Prompts are dynamically generated to guide LLM responses
* Additional results are filtered for quality
* Python version is 3.11.13

---

## ❗ Limitations

* Time zone logic and flight number verification are not yet included
* Currently English-only

---

## 🧠 Status

> This project is in its **testing phase**. It uses **free public APIs** (Gemma, OCR.Space, etc.), so performance may vary. Ideal for personal use, demos, and future scaling — not production-ready yet.

---

