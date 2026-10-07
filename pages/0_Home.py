import pandas as pd
import streamlit as st

import ui
from core.data import BOOKS

k = ui.header("ThaiRx-AI", "วิเคราะห์ · คัดเลือก · ค้นพบ ตำรับยาไทยอย่างอธิบายได้")
st.write("แพลตฟอร์มสำหรับ **แพทย์แผนไทย นักวิจัย และนักศึกษา** ใช้ข้อมูลตำรับจาก 3 แหล่ง "
         "แสดงเหตุผลและแหล่งที่มาของทุกผลลัพธ์ และส่งต่อให้ผู้เชี่ยวชาญตรวจสอบทุกชั้น")

c = st.columns(3)
with c[0], st.container(border=True):
    st.markdown("### 🎯 คัดเลือกตำรับ")
    st.caption("ใส่อาการ/ข้อบ่งใช้ → ตรวจเกรดสมุนไพรทุกตัว → แยกตำรับที่พร้อมพัฒนา กับที่ยังมีข้อจำกัด")
    st.page_link("pages/1_Recommend.py", label="ไปหน้าคัดเลือก →")
with c[1], st.container(border=True):
    st.markdown("### 🔍 วิเคราะห์ตำรับ")
    st.caption("ข้อความตามตำรา · รูปแบบจากฐานข้อมูล · หลักฐานวิจัยสมัยใหม่ แยกกันชัดเจน")
    st.page_link("pages/2_Analyze.py", label="ไปหน้าวิเคราะห์ →")
with c[2], st.container(border=True):
    st.markdown("### 🧪 สร้างสมมติฐาน")
    st.caption("เสนอชุดสมุนไพรจากรูปแบบที่ค้นพบ เพื่อให้ผู้เชี่ยวชาญประเมิน (ไม่ใช่สูตรยา)")
    st.page_link("pages/3_Discover.py", label="ไปหน้าสร้างสมมติฐาน →")

st.markdown("### สถานะข้อมูล")
rec = k.recipes
split = set(k.items["recipe_id"])
sym = set(k.t["recipe_symptoms"]["recipe_id"])
ind = set(k.t["recipe_indications"]["recipe_id"])
st.dataframe(pd.DataFrame([{
    "แหล่ง": ui.book_label(b),
    "ตำรับ": int((rec["book"] == b).sum()),
    "แยกสมุนไพรแล้ว": int(rec.loc[rec["book"] == b, "recipe_id"].isin(split).sum()),
    "มีอาการ": int(rec.loc[rec["book"] == b, "recipe_id"].isin(sym).sum()),
    "มีข้อบ่งใช้": int(rec.loc[rec["book"] == b, "recipe_id"].isin(ind).sum()),
    "ซ้ำกับแหล่งอื่น": int(((rec["book"] == b) & (rec["duplicate_of"] != "")).sum()),
} for b in BOOKS]), hide_index=True, width="stretch")

herbs_used = set(k.items.loc[k.items["resolved"], "herb_id"])
graded = herbs_used & set(k.t["herb_grades"]["herb_id"])
m = st.columns(4)
m[0].metric("สมุนไพรที่ใช้ในตำรับ (ยืนยันชื่อแล้ว)", len(herbs_used))
m[1].metric("มีเกรดแล้ว", f"{len(graded)}/{len(herbs_used)}")
pend = k.pending_counts()
m[2].metric("ชื่อสมุนไพรรอตรวจสอบ", pend["ชื่อสมุนไพรที่ยังไม่ยืนยัน"])
m[3].metric("ชื่อพ้องรอตรวจสอบ", pend["ชื่อพ้องรอตรวจสอบ"])

st.markdown("### สถาปัตยกรรม 4 ชั้น")
st.markdown(
    "1. **Traditional Knowledge Data Layer**: ตำรับ ข้อบ่งใช้ อาการ สมุนไพร ส่วนที่ใช้ ปริมาณ + ข้อความต้นฉบับ → หน้าวิเคราะห์\n"
    "2. **Knowledge Discovery Layer**: Apriori (support / confidence / lift + จำนวนตำรับจริง) → ใช้ร่วมทุกหน้า\n"
    "3. **Recommendation / Reasoning Layer**: ประตูความพร้อมจากเกรดสมุนไพร แล้วเรียงตามความเกี่ยวข้อง → หน้าคัดเลือก\n"
    "4. **Formula Discovery Layer**: เสนอชุดสมุนไพรจากรูปแบบที่ค้นพบ → หน้าสร้างสมมติฐาน\n\n"
    "ผู้เชี่ยวชาญตรวจสอบ (Human-in-the-loop) ทุกชั้น บันทึกผู้ตรวจ สถานะ และเวอร์ชันข้อมูลที่ Back-end"
)
ui.footer()
