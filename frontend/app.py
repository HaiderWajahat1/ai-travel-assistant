import streamlit as st
import requests

st.set_page_config(page_title="Travel Planner Pro", layout="wide")  # wide display

st.markdown("""
    <style>
        .main h2 { color: #228be6; }
        .main h3 { color: #7c3aed; }
        .main ul { margin-left: 1.5em; }
        .main strong { color: #fa5252; }
    </style>
""", unsafe_allow_html=True)

st.title("📷 Upload Travel Document")
st.write("Upload a boarding pass or ticket image (PNG/JPG) and get your itinerary.")

# --- File uploader block ---
uploaded = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])

if uploaded:
    st.image(uploaded, caption="Uploaded Image", use_container_width=True)  # modern parameter

    if st.button("Generate Itinerary"):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        with st.spinner("🧭 Processing..."):
            resp = requests.post(
                "http://localhost:8000/display-itinerary",  # Use your backend URL here
                files=files
            )
        if resp.ok:
            data = resp.json()
            st.success("✅ Itinerary generated!")
            st.header("✈️ Trip Summary")
            # Save itinerary to session state for chat context
            st.session_state['itinerary'] = data["itinerary"]["output"]
            # Clear any previous chat answer
            st.session_state['chat_answer'] = ""
        else:
            st.error(f"Error: {resp.status_code} - {resp.text}")
            st.session_state['itinerary'] = None
            st.session_state['chat_answer'] = ""
else:
    st.info("Please upload a boarding pass or ticket image to get started.")

# --- Show itinerary if exists in session ---
if st.session_state.get('itinerary'):
    st.markdown(st.session_state['itinerary'])

    # --- Chat bar with session-aware answer, no reset ---
    st.subheader("💬 Ask Anything About Your Trip")
    with st.form(key="chat_form"):
        user_query = st.text_input(
            "Ask a travel question (e.g., 'Show only restaurants near the airport', 'Best hiking spots nearby', etc.)",
            key="user_query_input"
        )
        submit_chat = st.form_submit_button(label="Ask")
    if submit_chat and user_query:
        with st.spinner("Getting your answer..."):
            resp3 = requests.post(
                "http://localhost:8000/ask",  # Use your backend URL here
                json={"user_query": user_query}
            )
        if resp3.ok:
            st.session_state['chat_answer'] = resp3.json()["answer"]
        else:
            st.session_state['chat_answer'] = f"Query failed: {resp3.status_code} - {resp3.text}"

    # Show the chat answer below the form
    if st.session_state.get('chat_answer'):
        st.markdown("---")
        st.header("💡 AI Answer")
        st.markdown(st.session_state['chat_answer'])

