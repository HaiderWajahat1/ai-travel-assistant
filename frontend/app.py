import streamlit as st
import requests

st.set_page_config(page_title="Travel Planner Pro", layout="centered")

# (Optional) Custom CSS for a slightly enhanced look
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

uploaded = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
if uploaded:
    st.image(uploaded, caption="Uploaded Image", use_column_width=True)
    if st.button("Generate Itinerary"):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        with st.spinner("🧭 Processing..."):
            resp = requests.post(
                "https://ai-travel-assistant-1-f396.onrender.com/display-itinerary",
                files=files
            )
        if resp.ok:
            data = resp.json()
            st.success("✅ Itinerary generated!")
            st.header("✈️ Trip Summary")
            # Show the pretty, formatted itinerary!
            if "itinerary" in data and "output" in data["itinerary"]:
                st.markdown(data["itinerary"]["output"])
                # --- Customization Chat Bar ---
                st.subheader("💬 Customize Your Itinerary")

                # Store the original itinerary markdown as the "base prompt"
                base_prompt = data["itinerary"]["output"]

                user_custom = st.text_input(
                    "How do you want to customize your itinerary? (e.g., 'Show only places near the airport')"
                )

                if st.button("Submit Custom Request"):
                    with st.spinner("Updating itinerary..."):
                        resp2 = requests.post(
                            "https://ai-travel-assistant-1-f396.onrender.com/custom-itinerary",   # Backend custom endpoint
                            json={
                                "base_prompt": base_prompt,
                                "user_input": user_custom
                            }
                        )
                    if resp2.ok:
                        custom_data = resp2.json()
                        st.markdown("---")
                        st.header("📝 Customized Itinerary")
                        st.markdown(custom_data["itinerary"])
                    else:
                        st.error(f"Custom itinerary failed: {resp2.status_code} - {resp2.text}")
            else:
                st.warning("No formatted itinerary output found.")
        else:   
            st.error(f"Error: {resp.status_code} - {resp.text}")

else:
    st.info("Please upload a boarding pass or ticket image to get started.")
