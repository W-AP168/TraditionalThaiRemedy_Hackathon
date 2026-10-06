"""Back-end · ข้อมูล & ตรวจสอบ: import, review queue, reviewer log."""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import streamlit as st

import ui
from core import rules as R
from core.data import DATA_DIR, SCHEMA, log_review, read_table, save_table
from core.ingest import build_tables, current_reference, list_versions, publish, read_sources

STATUS = ["pending", "verified", "rejected"]


def _save(name: str, df: pd.DataFrame, action: str, detail: str) -> None:
    k = ui.kb()
    save_table(name, df)
    log_review(st.session_state["reviewer"], action, name, detail, k.version)
    ui.refresh()
    st.toast(f"บันทึกแล้ว: {detail}")
    st.rerun()


def _zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DATA_DIR.glob("*.csv")) + [DATA_DIR / "dataset.json", DATA_DIR / "settings.json"]:
            if p.exists():
                z.write(p, f"data/{p.name}")
    return buf.getvalue()


def render() -> None:
    k = ui.kb()
    reviewer = st.session_state.get("reviewer", "")

    # ---------- import ----------
    st.markdown("### นำเข้า / อัปเดตข้อมูล")
    st.caption("CSV หรือ Excel (ทั้งไฟล์ ทุกชีต) ตั้งชื่ออย่างไรก็ได้ ระบบดูจากคอลัมน์ · คัมภีร์ดูจากรหัสตำรับ (WRO… NR… RM…) "
               "· ตารางอ้างอิง (ชื่อมาตรฐาน ชื่อพ้อง คณาเภสัช เกรด คำเตือน) ถ้าไม่อัปโหลดจะใช้ของเดิม")
    ups = st.file_uploader("เลือกไฟล์", type=["csv", "xlsx", "xls"], accept_multiple_files=True)
    raw = sorted(p for p in (DATA_DIR / "raw").glob("*") if p.suffix.lower() in (".csv", ".xlsx", ".xls")) \
        if (DATA_DIR / "raw").exists() else []
    c1, c2 = st.columns(2)
    if c1.button("ตรวจไฟล์ที่อัปโหลด", disabled=not ups, type="primary", width="stretch"):
        st.session_state["import"] = read_sources([(f.name, f.getvalue()) for f in ups])
    if c2.button(f"ตรวจไฟล์ใน data/raw ({len(raw)})", disabled=not raw, width="stretch"):
        st.session_state["import"] = read_sources([(p.name, p) for p in raw])

    imp = st.session_state.get("import")
    if imp is not None:
        st.dataframe(pd.DataFrame([{"ไฟล์/ชีต": s.name, "เป็นตาราง": ", ".join(s.kinds), "แหล่ง": s.book,
                                    "แถว": s.rows, "หมายเหตุ": s.note} for s in imp.sources]),
                     hide_index=True, width="stretch")
        tables, checks = build_tables(imp, current_reference())
        for c in checks:
            st.write(("✅ " if c.ok else ("⛔ " if c.blocking else "⚠️ ")) + c.detail)
            if not c.ok and c.rows is not None and not c.rows.empty:
                with st.expander("ดูรายการ"):
                    st.dataframe(c.rows, hide_index=True, width="stretch")
        if not any(c.blocking for c in checks):
            with st.form("publish"):
                v = st.text_input("เวอร์ชันข้อมูลใหม่", placeholder="เช่น 0.2")
                note = st.text_input("บันทึก", placeholder="เช่น WRO+NR รอบทำความสะอาด 2")
                if st.form_submit_button("เผยแพร่ข้อมูล", type="primary"):
                    if not v.strip() or not reviewer:
                        st.error("ต้องใส่เวอร์ชัน และชื่อผู้ตรวจ (ด้านบน)")
                    else:
                        publish(tables, v.strip().lstrip("v"), note)
                        log_review(reviewer, "publish", "*", note, v.strip())
                        ui.refresh()
                        R.precompute(ui.kb())
                        del st.session_state["import"]
                        st.success(f"เผยแพร่ข้อมูล v{v} แล้ว คำนวณกฎล่วงหน้าเรียบร้อย")

    st.info("บน Streamlit Cloud ไฟล์ที่เผยแพร่จะหายเมื่อแอปรีสตาร์ต: ดาวน์โหลด zip → แตกทับโฟลเดอร์ data/ → commit ขึ้น GitHub",
            icon="💾")
    st.download_button(f"ดาวน์โหลดข้อมูล v{k.version} (.zip)", _zip(), file_name=f"thairx_data_v{k.version}.zip")

    # ---------- review queue ----------
    st.markdown("### คิวตรวจสอบ (รอตรวจสอบ)")
    st.dataframe(pd.DataFrame([k.pending_counts()]), hide_index=True, width="stretch")
    if not reviewer:
        st.warning("ใส่ชื่อผู้ตรวจด้านบนก่อนแก้ไข ทุกการแก้ไขจะบันทึกชื่อและเวอร์ชันข้อมูล")
        return

    q1, q2, q3, q4, q5, q6 = st.tabs(["ชื่อสมุนไพร", "ชื่อพ้อง", "คณาเภสัช", "อาการ ↔ คำสมัยใหม่", "ตำรับ", "คำเตือนความปลอดภัย"])
    with q1:
        un = k.items[~k.items["resolved"]].groupby("herb_name_original")["recipe_id"].nunique() \
            .sort_values(ascending=False)
        if un.empty:
            st.success("ไม่มีชื่อสมุนไพรรอตรวจสอบ")
        else:
            st.caption("ไม่รวมชื่ออัตโนมัติ: เลือกว่าเป็นชื่อมาตรฐานใหม่ หรือเป็นชื่อพ้องของสมุนไพรที่มีอยู่")
            name = st.selectbox("ชื่อที่รอตรวจสอบ", un.index.tolist(), format_func=lambda n: f"{n} ({un[n]} ตำรับ)")
            how = st.radio("ตัดสิน", ["ชื่อมาตรฐานใหม่", "ชื่อพ้องของสมุนไพรที่มีอยู่"], horizontal=True)
            herbs = k.t["herbs"]
            if how == "ชื่อมาตรฐานใหม่":
                std = st.text_input("ชื่อมาตรฐาน", value=name)
                sci = st.text_input("ชื่อวิทยาศาสตร์ (ถ้าทราบ)")
                if st.button("ยืนยันเป็นชื่อมาตรฐาน", type="primary"):
                    row = {"herb_id": std, "std_name_th": std, "sci_name": sci, "review_status": "verified"}
                    df = pd.concat([herbs[herbs["herb_id"] != std], pd.DataFrame([row])], ignore_index=True)
                    if std != name:
                        syn = pd.concat([k.t["herb_synonyms"], pd.DataFrame([{
                            "alias": name, "herb_id": std, "reviewed_by": reviewer, "review_status": "verified"}])])
                        save_table("herb_synonyms", syn)
                    _save("herbs", df, "approve_herb", f"{name} → ชื่อมาตรฐาน {std}")
            else:
                target = st.selectbox("เป็นชื่อพ้องของ", herbs["herb_id"].tolist())
                if st.button("ยืนยันชื่อพ้อง", type="primary"):
                    syn = k.t["herb_synonyms"]
                    syn = pd.concat([syn[syn["alias"] != name], pd.DataFrame([{
                        "alias": name, "herb_id": target, "reviewed_by": reviewer, "review_status": "verified"}])])
                    _save("herb_synonyms", syn, "map_alias", f"{name} → {target}")
    with q2:
        syn = st.data_editor(k.t["herb_synonyms"], num_rows="dynamic", hide_index=True, width="stretch", key="ed_syn",
                             column_config={"review_status": st.column_config.SelectboxColumn(options=STATUS)})
        if st.button("บันทึกชื่อพ้อง"):
            changed = syn["review_status"] == "verified"
            syn.loc[changed & (syn["reviewed_by"] == ""), "reviewed_by"] = reviewer
            _save("herb_synonyms", syn, "edit_synonyms", f"{int(changed.sum())} verified")
    with q3:
        st.caption("กลุ่มที่ verified เท่านั้นจะถูกแตกเป็นสมุนไพรสมาชิกก่อนวิเคราะห์ (เก็บ from_group ไว้ตรวจย้อน)")
        grp = st.data_editor(k.t["herb_groups"], num_rows="dynamic", hide_index=True, width="stretch", key="ed_grp",
                             column_config={"review_status": st.column_config.SelectboxColumn(options=STATUS)})
        if st.button("บันทึกคณาเภสัช"):
            grp.loc[(grp["review_status"] == "verified") & (grp["reviewed_by"] == ""), "reviewed_by"] = reviewer
            _save("herb_groups", grp, "edit_groups", f"{grp['group_name'].nunique()} กลุ่ม")
    with q4:
        st.caption("คำโบราณไม่เท่ากับการวินิจฉัยสมัยใหม่: การเทียบต้องมีเหตุผลและผู้เทียบ")
        sym = k.t["recipe_symptoms"]
        uniq = sym.groupby("symptom_original").agg(
            symptom_modern=("symptom_modern", "first"), mapping_reason=("mapping_reason", "first"),
            mapped_by=("mapped_by", "first"), ตำรับ=("recipe_id", "nunique")).reset_index()
        ed = st.data_editor(uniq, hide_index=True, width="stretch", disabled=["symptom_original", "ตำรับ"], key="ed_sym")
        if st.button("บันทึกการเทียบคำ"):
            bad = ed[(ed["symptom_modern"] != "") & (ed["mapping_reason"].fillna("") == "")]
            if not bad.empty:
                st.error(f"ต้องใส่เหตุผลการเทียบ: {', '.join(bad['symptom_original'])}")
            else:
                ed.loc[(ed["symptom_modern"] != "") & (ed["mapped_by"].fillna("") == ""), "mapped_by"] = reviewer
                m = ed.set_index("symptom_original")
                new = sym.copy()
                for col in ("symptom_modern", "mapping_reason", "mapped_by"):
                    new[col] = new["symptom_original"].map(m[col]).fillna("")
                _save("recipe_symptoms", new, "map_symptoms", f"{int((ed['symptom_modern'] != '').sum())} คำ")
    with q5:
        st.caption("ตั้ง duplicate_of = รหัสตำรับต้นทาง ถ้าตำรับนี้คัดลอกจากแหล่งอื่น (ไม่นับใน Apriori โดยค่าเริ่มต้น)")
        cols = ["recipe_id", "book", "name", "duplicate_of", "review_status"]
        ed = st.data_editor(k.recipes[cols], hide_index=True, width="stretch", disabled=["recipe_id", "book"],
                            key="ed_rec", column_config={"review_status": st.column_config.SelectboxColumn(options=STATUS)})
        if st.button("บันทึกตำรับ"):
            new = k.recipes.copy().set_index("recipe_id")
            new.update(ed.set_index("recipe_id")[["name", "duplicate_of", "review_status"]])
            _save("recipes", new.reset_index(), "edit_recipes", "แก้สถานะ/ซ้ำ")
    with q6:
        st.caption("คำเตือนแยกจากเกรด: สมุนไพรที่ผ่านทั้งสองแกนก็ยังมีคำเตือนได้")
        saf = st.data_editor(k.t["herb_safety"], num_rows="dynamic", hide_index=True, width="stretch", key="ed_saf")
        if st.button("บันทึกคำเตือน"):
            if (saf["warning_text"].fillna("") != "").any() and (saf["source"].fillna("") == "").any():
                st.error("ทุกคำเตือนต้องมีแหล่งอ้างอิง")
            else:
                _save("herb_safety", saf, "edit_safety", f"{len(saf)} รายการ")

    st.markdown("### บันทึกการตรวจสอบ")
    log = read_table("review_log")[0]
    st.dataframe(log.iloc[::-1], hide_index=True, width="stretch")
    st.markdown("### ประวัติเวอร์ชัน")
    st.dataframe(pd.DataFrame([k.meta] + list_versions()), hide_index=True, width="stretch")
