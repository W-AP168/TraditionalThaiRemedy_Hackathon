import streamlit as st

import ui
from core import cache
from preprocessing.prepare_data import list_versions, prepare, publish, read_excel

if not ui.lab_gate():
    st.stop()

d = ui.ds()
st.caption("DATA MANAGEMENT")
st.title("ชุดข้อมูลปัจจุบัน")

left, right = st.columns(2, gap="large")
with left, st.container(border=True):
    st.markdown(f"### Dataset v{d.meta.get('version', '?')}")
    if d.meta.get("is_sample"):
        st.caption("ข้อมูลตัวอย่าง (สังเคราะห์) สำหรับทดสอบระบบ")
    raw = d.ingredients  # after synonym mapping
    unmapped = sorted(set(raw["herb_id"]) - set(d.herbs["herb_id"]))
    m = st.columns(2)
    m[0].metric("ตำรับ", f"{d.n_recipes:,}")
    m[1].metric("แถวส่วนประกอบ", f"{len(raw):,}")
    m[0].metric("อาการ", f"{d.n_symptoms:,}")
    m[1].metric("ชื่อที่ยังไม่จับคู่", len(unmapped))
    st.caption(f"อัปเดตล่าสุด: {d.meta.get('updated', '?')} · fingerprint {d.fingerprint}")
    if unmapped:
        with st.expander("ชื่อสมุนไพรที่ไม่อยู่ใน herbs.csv"):
            st.write(", ".join(unmapped))

with right, st.container(border=True):
    st.markdown("### อัปโหลดชุดข้อมูลใหม่")
    st.caption("Excel หนึ่งไฟล์ ชีต prescriptions, ingredients, symptoms (+ herbs, herb_synonyms ถ้ามี) "
               "คอลัมน์เหมือนไฟล์ใน data/")
    up = st.file_uploader("Upload new Excel", type=["xlsx"])

if up:
    rep = prepare(read_excel(up))
    st.markdown("### ผลตรวจข้อมูล")
    for c in rep.checks:
        icon = "✅" if c.ok else ("⛔" if c in rep.blocking else "⚠️")
        st.write(f"{icon} {c.detail}")
        if not c.ok and c.rows is not None and not c.rows.empty:
            with st.expander("ดูรายการ"):
                st.dataframe(c.rows, hide_index=True, width="stretch")
    if rep.can_publish:
        with st.form("publish"):
            v = st.text_input("เวอร์ชันใหม่", placeholder="เช่น 1.0")
            note = st.text_input("บันทึกการเปลี่ยนแปลง", placeholder="เช่น เพิ่มคัมภีร์ RM รวมชื่อพ้อง 38 คู่")
            if st.form_submit_button("Publish dataset", type="primary") and v:
                publish(rep, v.strip().lstrip("v"), note)
                cache.clear()
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success(f"เผยแพร่ v{v} แล้ว ผลวิเคราะห์ทุกหน้าคำนวณใหม่จากข้อมูลชุดนี้")
                st.rerun()
    else:
        st.error("แก้ข้อผิดพลาด ⛔ ใน Excel ก่อน แล้วอัปโหลดใหม่")

st.markdown("### Pipeline")
st.markdown("Upload Excel → Validate sheets → Normalize names → Apply synonyms → Check duplicates → "
            "Check missing values → Generate CSV → Binary matrix → Run analysis → **Publish**")

st.markdown("### ประวัติเวอร์ชัน")
history = [{"version": d.meta.get("version"), "updated": d.meta.get("updated"), "note": d.meta.get("note", ""),
            "status": "ใช้งาน"}]
history += [{"version": v.get("version"), "updated": v.get("updated"), "note": v.get("note", ""), "status": ""}
            for v in list_versions()]
st.dataframe(history, hide_index=True, width="stretch")
st.caption("ผลสถิติผูกกับเวอร์ชันข้อมูล เพราะการรวมชื่อพ้องเปลี่ยนค่า Lift ได้")

if st.button("ล้างแคชผลวิเคราะห์"):
    n = cache.clear()
    st.cache_data.clear()
    st.toast(f"ลบแคช {n} ไฟล์")
