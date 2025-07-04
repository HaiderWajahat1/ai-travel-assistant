import streamlit as st
import requests
import re

st.set_page_config(page_title="Travel Planner Pro", layout="wide")
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

# Session state
st.session_state.setdefault('is_generating', False)
st.session_state.setdefault('uploaded', None)
st.session_state.setdefault('itinerary', "")
st.session_state.setdefault('chat_answer', "")

st.title("📸 Upload Travel Document")
st.write("Upload a boarding pass or ticket to generate your itinerary.")

# Two-column upload + button layout
col1, col2 = st.columns([2, 3])
with col1:
    uploaded = st.file_uploader("", type=["png", "jpg", "jpeg"], width="stretch")
    if uploaded:
        st.session_state.uploaded = uploaded

with col2:
    if st.session_state.uploaded:
        st.image(st.session_state.uploaded, caption="Preview", use_container_width=True)

    # Render Generate or Cancel button
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
                st.session_state.itinerary = resp.json().get("itinerary", {}).get("output", "")
                st.session_state.chat_answer = ""
            else:
                st.error(f"Error {resp.status_code}: {resp.text}")
            st.session_state.is_generating = False
    else:
        if st.button("Cancel", use_container_width=True):
            st.session_state.is_generating = False
            st.info("Generation canceled.")

# Display itinerary full-width under upload section
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
            ans = result.get("answer", "")
            if isinstance(ans, dict):
                st.session_state.chat_answer = ans.get("output", "")
            else:
                st.session_state.chat_answer = ans
        else:
            st.session_state.chat_answer = f"Error {resp.status_code}: {resp.text}"

    if st.session_state.chat_answer:
        st.markdown("---")
        st.markdown(format_links(st.session_state.chat_answer), unsafe_allow_html=False)
