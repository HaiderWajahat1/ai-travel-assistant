import streamlit as st
import requests
from streamlit_folium import st_folium
from route import build_basic_route_map

### 🆕 PDF-related imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
import re
import os

st.set_page_config(page_title="AI Travel Planner", layout="wide")
st.markdown("""
<style>
  [data-testid="stSidebar"] {width: 280px;}
  .main .block-container {padding: 40px;}
</style>
""", unsafe_allow_html=True)

def format_links(text):
    return re.sub(r'\[([^\]]+)\]\((http[^\)]+)\)', r'[Website Link](\2)', text)

class LogoRightCorner(Flowable):
    def __init__(self, path, size=0.6 * inch):
        super().__init__()
        self.img_path = path
        self.width = size
        self.height = size

    def draw(self):
        self.canv.drawImage(self.img_path, self.canv._pagesize[0] - self.width - 40, self.canv._pagesize[1] - self.height - 30, width=self.width, height=self.height, mask='auto')

def generate_pdf(itinerary_text: str, destination: str = "", logo_path: str = "assets/logo.png") -> bytes:
    buffer = BytesIO()

    safe_destination = re.sub(r'[^\w\- ]+', '', destination).replace(" ", "_").lower()

    # Prepare styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CoverTitle', fontSize=28, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CoverSubtitle', fontSize=16, alignment=TA_CENTER, spaceAfter=10))
    styles.add(ParagraphStyle(name='MainHeading', fontSize=18, spaceAfter=16, spaceBefore=18, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubHeading', fontSize=14, spaceAfter=10, spaceBefore=14, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='NormalText', fontSize=11.5, leading=16, alignment=TA_LEFT))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=60, bottomMargin=40,
        title=f"Travel Itinerary for {destination or 'Destination'}"
    )

    elements = []

    # Load logo if exists
    show_logo = os.path.exists(logo_path)

    # --- Cover Page ---
    elements.append(Spacer(1, 100))
    elements.append(Paragraph("Travel Itinerary", styles['CoverTitle']))
    elements.append(Paragraph(f"Destination: {destination or 'Unknown'}", styles['CoverSubtitle']))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['CoverSubtitle']))
    if show_logo:
        elements.append(Spacer(1, 50))
        elements.append(Image(logo_path, width=1.5 * inch, height=1.5 * inch, hAlign='CENTER'))
    elements.append(PageBreak())

    # Insert corner logo on each page except cover
    def corner_logo():
        return LogoRightCorner(logo_path) if show_logo else None

    # Line filtering + formatting
    def is_bare_url(line):
        return line.startswith("http://") or line.startswith("https://")

    def strip_markdown(text: str) -> str:
        return re.sub(r'\*\*(.*?)\*\*', r'\1', text)

    major_sections = {"restaurants", "hotels", "rental cars", "weather forecast"}

    def parse_line(line):
        line = line.strip()
        if is_bare_url(line):
            return None

        # Replace markdown links with clickable [Website Link]
        line = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<link href="\2"><u>[Website Link]</u></link>', line)
        line = strip_markdown(line)

        # Major section (force page break + top-right logo)
        if line.lower().replace(" ", "") in major_sections:
            elements.append(PageBreak())
            logo_flow = corner_logo()
            if logo_flow:
                elements.append(logo_flow)
            return Paragraph(line.title(), styles['MainHeading'])

        elif line.startswith("###") or line.startswith("####"):
            cleaned = re.sub(r"#+", "", line).replace("■", "").strip()
            return Paragraph(cleaned, styles['SubHeading'])

        elif line.startswith("- "):
            return Paragraph(line[2:].strip(), styles['NormalText'])

        elif line:
            return Paragraph(line, styles['NormalText'])

        else:
            return Spacer(1, 6)

    # Build content
    for raw_line in itinerary_text.splitlines():
        element = parse_line(raw_line)
        if element:
            elements.append(element)
            elements.append(Spacer(1, 4))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# Sidebar
with st.sidebar:
    st.header("⚙️ Customize Your Trip")
    num_suggestions = st.number_input(
        "Number of suggestions per category",
        min_value=1, max_value=10, value=3, step=1
    )
    free_prefs = st.text_area(
        "Preferences (comma-separated)",
        placeholder="e.g. vegetarian, hiking, skip hotel, have a car",
        height=100
    )

    st.markdown("### 🕘 Chat History")
    for i, chat in enumerate(st.session_state.get("chat_history", []), 1):
        st.markdown(f"**{i}.** {chat['question']}")

# Session state
st.session_state.setdefault('is_generating', False)
st.session_state.setdefault('uploaded', None)
st.session_state.setdefault('itinerary', "")
st.session_state.setdefault('chat_answer', "")
st.session_state.setdefault('chat_history', [])
st.session_state.setdefault('chat_summary', "")
st.session_state.setdefault('city', "")
st.session_state.setdefault('airport', "")
st.session_state.setdefault('arrival_time', "")

st.title("AI Travel Planner")

# Upload section
uploaded = st.file_uploader(
    "Upload your boarding pass or travel ticket (JPG, PNG, JPEG)",
    type=["png", "jpg", "jpeg"],
    key="file_uploader",
    label_visibility="visible"
)
if uploaded:
    st.session_state.uploaded = uploaded

# Generate button
if not st.session_state.is_generating:
    if st.session_state.uploaded and st.button("Generate Itinerary", use_container_width=True):
        st.session_state.is_generating = True
        files = {
            "file": (
                st.session_state.uploaded.name,
                st.session_state.uploaded.getvalue(),
                st.session_state.uploaded.type
            )
        }
        data = {"preferences": free_prefs, "top_k": num_suggestions}
        with st.spinner("🧭 Generating itinerary..."):
            resp = requests.post("http://localhost:8000/display-itinerary", files=files, data=data)
        if resp.ok:
            resp_data = resp.json()
            st.session_state["itinerary_origin"] = resp_data.get("origin", "")
            st.session_state["city"] = resp_data.get("city", "")
            st.session_state["airport"] = resp_data.get("airport", "")
            st.session_state["arrival_time"] = resp_data.get("arrival_time", "")

            itinerary = resp_data.get("itinerary", {})
            st.session_state.itinerary = itinerary.get("output", "") if isinstance(itinerary, dict) else itinerary
            st.session_state.chat_answer = ""
        else:
            st.error(f"Error {resp.status_code}: {resp.text}")
        st.session_state.is_generating = False
else:
    if st.button("Cancel", use_container_width=True):
        st.session_state.is_generating = False
        st.info("Generation canceled.")

# Show image + map side-by-side
if st.session_state.uploaded and st.session_state.itinerary:
    col_img, col_map = st.columns([1, 1])
    with col_img:
        st.image(st.session_state.uploaded, caption="Preview", use_container_width=True)
    with col_map:
        origin = st.session_state.get("itinerary_origin")
        destination = st.session_state.get("city")
        if origin and destination:
            st.markdown(f"### 🗺️ Route Preview: {origin} → {destination}")
            route_map = build_basic_route_map(origin, destination)
            if route_map:
                st_folium(route_map, width=340, height=250)
            else:
                st.warning("Could not generate map — check city names.")

# Show itinerary
if st.session_state.itinerary:
    st.markdown("---")
    st.markdown(format_links(st.session_state.itinerary), unsafe_allow_html=False)

    ### 🆕 PDF download button
    destination = st.session_state.get("city", "").strip()
    pdf_bytes = generate_pdf(st.session_state.itinerary, destination, logo_path="assets/logo.png")


    safe_destination = re.sub(r'[^\w\- ]+', '', destination).replace(" ", "_").lower()
    file_name = f"travel_itinerary_{safe_destination or 'destination'}.pdf"

    st.download_button(
        label="📄 Download Itinerary as PDF",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf"
    )


    # Chat form
    st.subheader("💬 Ask Anything About Your Trip")
    with st.form("chat_form", clear_on_submit=False):
        user_query = st.text_input("e.g. Best hikes nearby?", key="chat_input")
        submitted = st.form_submit_button("Ask")

    if submitted and user_query:
        with st.spinner("Thinking..."):
            resp = requests.post("http://localhost:8000/ask", json={"user_query": user_query})
        if resp.ok:
            result = resp.json()
            st.session_state.chat_answer = result.get("answer", "")
            st.session_state.chat_history = result.get("history", [])
            st.session_state.chat_summary = result.get("summary", "")
        else:
            st.session_state.chat_answer = f"Error {resp.status_code}: {resp.text}"

    if st.session_state.chat_answer:
        st.markdown("---")
        st.markdown(format_links(st.session_state.chat_answer), unsafe_allow_html=False)

        if st.session_state.chat_summary:
            st.markdown("#### 📜 Earlier Chat Summary")
            st.markdown(st.session_state.chat_summary)
