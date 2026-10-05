"""ตำรับยาไทย — Thai Traditional Medicine Knowledge System.

    streamlit run app.py
"""

import streamlit as st

import ui

st.set_page_config(page_title="ตำรับยาไทย", page_icon="🌿", layout="wide")
ui.setup()

explore = [
    st.Page("pages/home.py", title="หน้าแรก", icon="🏠", default=True),
    st.Page("pages/explore.py", title="สำรวจตำรับ", icon="📜"),
    st.Page("pages/symptoms.py", title="ค้นหาอาการ", icon="🔎"),
    st.Page("pages/herbs.py", title="คลังสมุนไพร", icon="🌿"),
    st.Page("pages/about.py", title="เกี่ยวกับโครงการ", icon="ℹ️"),
    st.Page("pages/recipe.py", title="รายละเอียดตำรับ", icon="📄", visibility="hidden"),
]
lab = [
    st.Page("pages/research.py", title="Research Dashboard", icon="📊"),
    st.Page("pages/apriori_lab.py", title="Apriori Lab", icon="🧪"),
    st.Page("pages/statistics.py", title="หลักฐานทางสถิติ", icon="📈"),
    st.Page("pages/graph.py", title="Knowledge Graph", icon="🕸️"),
    st.Page("pages/admin.py", title="จัดการข้อมูล", icon="🗂️"),
]

nav = st.navigation({"Explore": explore, "Research Lab 🔬": lab}, position="top")
nav.run()
