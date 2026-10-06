import streamlit as st

import ui
from backend import data_tab, eval_tab, grades_tab, rules_tab

if not ui.backend_gate():
    ui.footer()
    st.stop()

k = ui.header("Back-end", "สำหรับนักวิจัย / กรรมการ")
st.session_state["reviewer"] = st.text_input(
    "ชื่อผู้ตรวจ (บันทึกในทุกการแก้ไข)", value=st.session_state.get("reviewer", ""), placeholder="เช่น ภก. ...")

t1, t2, t3, t4 = st.tabs(["ข้อมูล & ตรวจสอบ", "เกรดสมุนไพร", "กฎความสัมพันธ์", "การประเมินผล"])
with t1:
    data_tab.render()
with t2:
    grades_tab.render()
with t3:
    rules_tab.render()
with t4:
    eval_tab.render()
ui.footer()
