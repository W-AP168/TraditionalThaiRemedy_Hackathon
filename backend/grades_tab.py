"""Back-end · เกรดสมุนไพร: editor, coverage, research-mode criteria, relevance weights."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import ui
from core.data import SCHEMA, log_review, save_settings, save_table
from core.gate import INDUSTRY, evaluate

REQUIRED = ["source", "reason", "assessor", "assessed_date"]


def render() -> None:
    k = ui.kb()
    reviewer = st.session_state.get("reviewer", "")
    ui.grade_legend()

    used = sorted(set(k.items.loc[k.items["resolved"], "herb_id"]))
    g = k.t["herb_grades"]
    graded_id = set(g.loc[g["identity"] != "", "herb_id"])
    graded_av = set(g.loc[g["availability"] != "", "herb_id"])
    c = st.columns(4)
    c[0].metric("สมุนไพรที่ใช้ในตำรับ", len(used))
    c[1].metric("มีเกรด Identity", f"{len(graded_id & set(used))}/{len(used)}")
    c[2].metric("มีเกรด Availability", f"{len(graded_av & set(used))}/{len(used)}")
    recs = k.items["recipe_id"].unique()
    ready = sum(evaluate(k, r, INDUSTRY).ready for r in recs)
    c[3].metric("ตำรับที่ผ่านเกณฑ์ Industry", f"{ready}/{len(recs)}",
                help="ถ้าน้อยมาก อาจเพราะสมุนไพร Availability A มีน้อย (ความเสี่ยงข้อ 12)")
    if len(g):
        dist = pd.crosstab(g["identity"].replace("", "?"), g["availability"].replace("", "?"))
        st.caption("การกระจายเกรด (แถว = Identity, คอลัมน์ = Availability)")
        st.dataframe(dist, width="stretch")

    st.markdown("### แก้ไขเกรด")
    st.caption("ทุกแถวที่มีเกรดต้องมี แหล่งอ้างอิง เหตุผล ผู้ประเมิน และวันที่ · สองแกนประเมินแยกกัน ห้ามอนุมานจากกัน")
    base = pd.DataFrame({"herb_id": used}).merge(g, on="herb_id", how="outer").fillna("")
    base = base.reindex(columns=SCHEMA["herb_grades"])
    ed = st.data_editor(base, hide_index=True, width="stretch", key="ed_grades", disabled=["herb_id"],
                        column_config={
                            "identity": st.column_config.SelectboxColumn("Identity", options=["", "A", "B", "C", "D"]),
                            "availability": st.column_config.SelectboxColumn("Availability",
                                                                             options=["", "A", "B", "C", "D", "E"])})
    if st.button("บันทึกเกรด", type="primary", disabled=not reviewer):
        has = (ed["identity"] != "") | (ed["availability"] != "")
        bad = ed[has & ed[REQUIRED].fillna("").eq("").any(axis=1)]
        if not bad.empty:
            st.error(f"ข้อมูลไม่ครบ (ต้องมี {', '.join(REQUIRED)}): {', '.join(bad['herb_id'])}")
        else:
            save_table("herb_grades", ed[has])
            log_review(reviewer, "edit_grades", "herb_grades", f"{int(has.sum())} สมุนไพร", k.version)
            ui.refresh()
            st.rerun()
    if not reviewer:
        st.caption("ใส่ชื่อผู้ตรวจด้านบนเพื่อบันทึก")

    st.markdown("### เกณฑ์โหมด Research")
    s = ui.conf()
    a, b = st.columns(2)
    ida = a.multiselect("Identity ที่ยอมรับ", list("ABCD"), default=s["research_identity_allowed"])
    ava = b.multiselect("Availability ที่ยอมรับ", list("ABCDE"), default=s["research_availability_allowed"])
    st.markdown("### น้ำหนักคะแนนความเกี่ยวข้อง (ค่าเริ่มต้น รอทีมยืนยัน)")
    a, b, c2 = st.columns(3)
    ws = a.number_input("น้ำหนักอาการ", 0.0, 5.0, float(s["weight_symptom"]), 0.1)
    wi = b.number_input("น้ำหนักข้อบ่งใช้", 0.0, 5.0, float(s["weight_indication"]), 0.1)
    low = c2.number_input("กฎ 'ข้อมูลน้อย' เมื่อจำนวนตำรับ <", 1, 50, int(s["low_support_count"]))
    st.caption(f"Industry คงที่: Identity ∈ {set(INDUSTRY.identity_allowed)}, Availability ∈ "
               f"{set(INDUSTRY.availability_allowed)}")
    if st.button("บันทึกการตั้งค่า", disabled=not reviewer):
        s.update({"research_identity_allowed": ida, "research_availability_allowed": ava,
                  "research_set_by": reviewer, "weight_symptom": ws, "weight_indication": wi,
                  "low_support_count": int(low)})
        save_settings(s)
        log_review(reviewer, "settings", "settings.json", str(s), k.version)
        ui.refresh()
        st.toast("บันทึกแล้ว")
