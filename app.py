"""ThaiRx-AI — explainable AI platform to analyze, recommend and discover Thai traditional medicine formulas.

    streamlit run app.py
"""

import streamlit as st

import ui

st.set_page_config(page_title="ThaiRx-AI", page_icon="🌿", layout="wide")
ui.setup()

pages = {
    "ThaiRx-AI": [
        st.Page("pages/0_Home.py", title="ภาพรวม", icon="🏠", default=True),
        st.Page("pages/1_Recommend.py", title="คัดเลือกตำรับ", icon="🎯"),
        st.Page("pages/2_Analyze.py", title="วิเคราะห์ตำรับ", icon="🔍"),
        st.Page("pages/3_Discover.py", title="สร้างสมมติฐาน", icon="🧪"),
    ],
    "Back-end 🔒": [
        st.Page("pages/9_Backend.py", title="Back-end", icon="🗂️"),
    ],
}
st.navigation(pages, position="top").run()
