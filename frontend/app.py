import streamlit as st
import requests

st.set_page_config(page_title="Travel Planner Pro", layout="centered")

st.title("📷 Upload Travel Document")
st.write("Upload a boarding pass or ticket image (PNG/JPG) and get your itinerary.")

uploaded = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
if uploaded:
    st.image(uploaded, caption="Uploaded Image", use_column_width=True)
    if st.button("Generate Itinerary"):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        with st.spinner("🧭 Processing..."):
            resp = requests.post("https://your-backend-username.onrender.com/process", files=files)

        if resp.ok:
            data = resp.json()
            st.success("✅ Itinerary generated!")
            st.header("✈️ Trip Summary")
            st.json(data, expanded=False)
        else:   
            st.error(f"Error: {resp.status_code} - {resp.text}")
