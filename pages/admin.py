import pandas as pd
import streamlit as st

import ui
from core import cache
from core.team_csv import SCRIPTURE_NAMES
from preprocessing.import_team_csvs import RAW_DIR, import_files
from preprocessing.prepare_data import list_versions, prepare, publish, read_excel

if not ui.lab_gate():
    st.stop()

d = ui.ds()
st.caption("DATA MANAGEMENT")
st.title("ชุดข้อมูลปัจจุบัน")

if msg := st.session_state.pop("published_msg", None):
    st.success(msg)

left, right = st.columns([2, 3], gap="large")
with left, st.container(border=True):
    st.markdown(f"### Dataset v{d.meta.get('version', '?')}")
    if d.meta.get("is_sample"):
        st.caption("ข้อมูลตัวอย่าง (สังเคราะห์) สำหรับทดสอบระบบ")
    unmapped = sorted(set(d.ingredients["herb_id"]) - set(d.herbs["herb_id"]))
    m = st.columns(2)
    m[0].metric("ตำรับ", f"{d.n_recipes:,}")
    m[1].metric("สมุนไพร", f"{d.n_herbs:,}")
    m[0].metric("อาการ", f"{d.n_symptoms:,}")
    m[1].metric("ชื่อที่ยังไม่จับคู่", len(unmapped))
    by_book = d.prescriptions["scripture_id"].value_counts()
    st.caption(" · ".join(f"{b} {by_book.get(b, 0)} ตำรับ" for b in SCRIPTURE_NAMES))
    st.caption(f"อัปเดตล่าสุด: {d.meta.get('updated', '?')} · fingerprint {d.fingerprint}")

with right, st.container(border=True):
    st.markdown("### นำเข้าข้อมูลใหม่")
    tab_csv, tab_xlsx = st.tabs(["CSV จากทีม (แนะนำ)", "Excel ไฟล์เดียว"])
    with tab_csv:
        st.caption(
            "ตั้งชื่อไฟล์อย่างไรก็ได้ ระบบดูจากคอลัมน์: มี **รหัสตำรับ + ชื่อสมุนไพร** = ไฟล์สมุนไพร, "
            "มี **รหัสตำรับ + อาการ/สรรพคุณ** = ไฟล์อาการ · คัมภีร์ดูจากรหัสตำรับ (WRO… NR… WP…) "
            "· ไฟล์ชื่อพ้องให้มีคำว่า synonym หรือ ชื่อพ้อง ในชื่อไฟล์"
        )
        ups = st.file_uploader("เลือกไฟล์ CSV (หลายไฟล์ได้)", type=["csv"], accept_multiple_files=True)
        raw_files = sorted(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []
        c1, c2 = st.columns(2)
        if c1.button("ตรวจไฟล์ที่อัปโหลด", disabled=not ups, type="primary", width="stretch"):
            st.session_state["import"] = ("upload", import_files([(f.name, f) for f in ups]))
        if c2.button(f"ตรวจไฟล์ในโฟลเดอร์ data/raw ({len(raw_files)})", disabled=not raw_files, width="stretch"):
            st.session_state["import"] = ("raw", import_files([(p.name, p) for p in raw_files]))
    with tab_xlsx:
        st.caption("ชีต prescriptions, ingredients, symptoms (+ herbs, herb_synonyms) คอลัมน์เหมือนไฟล์ใน data/")
        up = st.file_uploader("Upload Excel", type=["xlsx"])
        if up and st.button("ตรวจ Excel", type="primary"):
            st.session_state["import"] = ("excel", (None, prepare(read_excel(up)), []))

if "import" in st.session_state:
    source, (td, rep, notes) = st.session_state["import"]
    st.markdown("### ผลตรวจข้อมูล")
    if td is not None:
        kinds = {"herbs": "สมุนไพร", "symptoms": "อาการ", "both": "สมุนไพร + อาการ", "synonyms": "ชื่อพ้อง",
                 "skipped": "ข้าม"}
        st.dataframe(
            pd.DataFrame([{"ไฟล์": f.name, "ชนิด": kinds[f.kind], "คัมภีร์": f.book, "แถว": f.rows, "หมายเหตุ": f.note}
                          for f in td.files]),
            hide_index=True, width="stretch",
        )
        st.write(f"**{td.herbs['recipe_id'].nunique():,}** ตำรับ · **{td.herbs['herb'].nunique():,}** ชื่อสมุนไพร (ก่อนรวมชื่อพ้อง) · "
                 f"**{td.symptoms['symptom'].nunique():,}** อาการ")
    for n in notes:
        st.write(f"⚠️ {n}")
    for c in rep.checks:
        icon = "✅" if c.ok else ("⛔" if any(c is b for b in rep.blocking) else "⚠️")
        st.write(f"{icon} {c.detail}")
        if not c.ok and c.rows is not None and not c.rows.empty:
            with st.expander("ดูรายการ"):
                st.dataframe(c.rows, hide_index=True, width="stretch")
    if rep.can_publish:
        with st.form("publish"):
            v = st.text_input("เวอร์ชันใหม่", placeholder="เช่น 0.2")
            note = st.text_input("บันทึกการเปลี่ยนแปลง", placeholder="เช่น WRO + NR ทำความสะอาดรอบ 1")
            if st.form_submit_button("Publish dataset", type="primary") and v.strip():
                publish(rep, v.strip().lstrip("v"), note)
                cache.clear()
                st.cache_data.clear()
                st.cache_resource.clear()
                del st.session_state["import"]
                st.session_state["published_msg"] = f"เผยแพร่ v{v.strip()} แล้ว ทุกหน้าใช้ข้อมูลชุดนี้"
                st.rerun()
    else:
        st.error("แก้ข้อผิดพลาด ⛔ ก่อน แล้วตรวจใหม่")

st.markdown("### Pipeline")
st.markdown("CSV/Excel → ตรวจคอลัมน์ → แยกคัมภีร์ → ตัดช่องว่าง → รวมชื่อพ้อง → ตรวจซ้ำ/ค่าว่าง → "
            "Binary matrix → Apriori → Permutation test → **Publish**")

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
