import streamlit as st
import requests
import re
from streamlit_folium import st_folium
from route import build_basic_route_map

st.set_page_config(page_title="AI Travel Planner", layout="wide")
st.markdown("""
<style>
  [data-testid="stSidebar"] {width: 280px;}
  .main .block-container {padding: 40px;}
</style>
""", unsafe_allow_html=True)

def format_links(text):
    return re.sub(r'\[([^\]]+)\]\((http[^\)]+)\)', r'[Website Link](\2)', text)

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
# st.write("Upload a boarding pass or ticket to generate your itinerary.")

# Upload section (always visible)
uploaded = st.file_uploader(
    "Upload your boarding pass or travel ticket (JPG, PNG, JPEG)",
    type=["png", "jpg", "jpeg"],
    key="file_uploader",
    label_visibility="visible"
)
if uploaded:
    st.session_state.uploaded = uploaded

# Generate button (always under upload)
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

# Show boarding pass image and map side-by-side, once itinerary is generated
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

# Itinerary directly after row, no extra gap
if st.session_state.itinerary:
    st.markdown("---")
    st.markdown(format_links(st.session_state.itinerary), unsafe_allow_html=False)

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
