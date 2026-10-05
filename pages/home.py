import streamlit as st

import ui

d = ui.ds()

st.markdown(
    f"""
<div class="hero">
  <div class="eyebrow">THAI TRADITIONAL MEDICINE KNOWLEDGE SYSTEM</div>
  <h1>จากคัมภีร์โบราณ<br>สู่หลักฐานเชิงข้อมูล</h1>
  <p>สำรวจตำรับยาไทยกว่า {d.n_recipes:,} ตำรับ และค้นพบรูปแบบความสัมพันธ์ของสมุนไพรที่ซ่อนอยู่ในภูมิปัญญาไทย</p>
  <div class="stats">
    <div><b>{d.n_scriptures}</b><span>คัมภีร์</span></div>
    <div><b>{d.n_recipes:,}</b><span>ตำรับ</span></div>
    <div><b>{d.n_herbs:,}</b><span>สมุนไพร</span></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)
st.page_link("pages/explore.py", label="เริ่มสำรวจตำรับยา →")
ui.sample_banner()

st.markdown("## คุณต้องการค้นหาจากอะไร?")
c1, c2 = st.columns(2, gap="large")
with c1, st.container(border=True):
    st.markdown("### 🔎 ค้นหาจากอาการ")
    st.write("ฉันต้องการสำรวจตำรับที่เกี่ยวข้องกับอาการ เช่น ไข้ ไอ ท้องอืด")
    st.page_link("pages/symptoms.py", label="ไปค้นหาจากอาการ →")
with c2, st.container(border=True):
    st.markdown("### 🌿 ค้นหาจากสมุนไพร")
    st.write("ฉันต้องการดูว่าสมุนไพรนี้ถูกใช้กับอะไร และมักใช้คู่กับสมุนไพรใด")
    st.page_link("pages/herbs.py", label="ไปคลังสมุนไพร →")

st.markdown("## จากต้นฉบับ สู่การค้นพบ")
steps = [
    ("01", "คัมภีร์โบราณ", "ตำรับจากคัมภีร์ เก็บพร้อมข้อความต้นฉบับ"),
    ("02", "ข้อมูลมีโครงสร้าง", "แยกสมุนไพร อาการ ชื่อพ้อง และตรวจความถูกต้อง"),
    ("03", "การค้นพบทางสถิติ", "Apriori หาคู่สมุนไพร แล้วทดสอบด้วย permutation test"),
    ("04", "มนุษย์ตีความ", "ผู้เชี่ยวชาญอ่านผลร่วมกับต้นฉบับ ไม่ใช่ข้อสรุปทางคลินิก"),
]
for col, (n, title, body) in zip(st.columns(4), steps):
    with col, st.container(border=True):
        st.markdown(f'<span class="mono" style="color:#7A5E1C">{n}</span>', unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        st.caption(body)

ui.disclaimer()
