"""Back-end · การประเมินผล (spec section 9).

Every block either shows a real computed number, or says "ข้อมูลไม่พอ" and what
input it is waiting for. Nothing is invented.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from core import rules as R
from core.data import BOOKS, DATA_DIR
from core.gate import INDUSTRY
from core.recommend import recommend
from core.scoring import match
from eval import gate_fixtures, precision

# fixed BEFORE looking at results; do not tune to reproduce the old manual choice
DEMO_QUERY = {"symptoms": ["ปวดข้อ"], "indications": [], "mode": "industry", "books": list(BOOKS)}


def _csv(name: str) -> pd.DataFrame | None:
    p = DATA_DIR / name
    return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig") if p.exists() else None


def _missing(what: str, file: str, cols: str) -> None:
    st.info(f"ข้อมูลไม่พอ: รอ{what} → วางไฟล์ `data/{file}` (คอลัมน์: {cols})")


def render() -> None:
    k = ui.kb()
    s = ui.conf()
    ui.md(ui.data_badge(k) + " ผลประเมินคำนวณจากข้อมูลชุดปัจจุบัน")

    # ---- system facts ----
    _, meta = ui.get_rules(R.DEFAULTS["herb_herb"])
    t0 = time.perf_counter()
    match(k, k.symptom_terms()[:3], [], list(BOOKS))
    search_ms = (time.perf_counter() - t0) * 1000
    c = st.columns(4)
    c[0].metric("เวอร์ชันข้อมูล", k.version)
    c[1].metric("อัปเดตล่าสุด", k.meta.get("updated", "-"))
    c[2].metric("เวลารัน Apriori", f"{meta.get('runtime_sec', 0)} s", help="สมุนไพร↔สมุนไพร ค่าเริ่มต้น (ครั้งที่คำนวณจริง)")
    c[3].metric("เวลาค้นหา", f"{search_ms:.0f} ms")

    # ---- data quality ----
    st.markdown("### 1 · คุณภาพข้อมูล")
    st.dataframe(pd.DataFrame([k.pending_counts()]), hide_index=True, width="stretch")
    dq = _csv("eval_data_quality.csv")
    if dq is None:
        _missing("ผลตรวจตัวอย่างโดยผู้เชี่ยวชาญเทียบต้นฉบับ", "eval_data_quality.csv", "recipe_id, field, correct (1/0)")
    else:
        err = 1 - (dq["correct"].str.strip() == "1").mean()
        st.metric("อัตราความผิดพลาด (ตัวอย่างที่ตรวจ)", f"{err:.1%}", help=f"ตรวจ {len(dq)} รายการ")

    # ---- retrieval ----
    st.markdown("### 2 · การค้นคืน / จัดอันดับ: Precision@5 เทียบ keyword search")
    q, lab = precision.load_inputs()
    if q is None or lab is None:
        _missing("ชุดคำถามและป้ายความเกี่ยวข้องที่ผู้เชี่ยวชาญตั้งไว้ล่วงหน้า", "eval_queries.csv + eval_labels.csv",
                 "query_id, symptoms, indications / query_id, recipe_id, relevant")
        tq, tl = precision.template()
        a, b = st.columns(2)
        a.download_button("แม่แบบ eval_queries.csv", tq, "eval_queries.csv")
        b.download_button("แม่แบบ eval_labels.csv", tl, "eval_labels.csv")
    else:
        res = precision.run(k, q, lab, 5, s["weight_symptom"], s["weight_indication"])
        st.dataframe(res, hide_index=True, width="stretch")
        a, b = st.columns(2)
        a.metric("P@5 เฉลี่ย ระบบ", f"{res['P@5 ระบบ'].mean():.2f}")
        b.metric("P@5 เฉลี่ย keyword", f"{res['P@5 keyword'].mean():.2f}")
        st.caption("ความเกี่ยวข้องตัดสินโดยผู้เชี่ยวชาญ (eval_labels.csv) ตำรับที่ไม่ได้ติดป้ายนับว่าไม่เกี่ยวข้อง · "
                   "คำถามชุดนี้ต้องไม่ใช้ปรับน้ำหนัก")

    # ---- traceability ----
    st.markdown("### 3 · การตรวจย้อนแหล่งที่มา")
    rec = k.recipes
    has_text = rec["original_text"] != ""
    ms = match(k, k.symptom_terms(), [], list(BOOKS))
    res_ids = [m.recipe_id for m in ms]
    ok = rec.set_index("recipe_id").loc[res_ids, "original_text"].ne("").mean() if res_ids else 0
    a, b = st.columns(2)
    a.metric("ตำรับที่มีข้อความต้นฉบับ", f"{has_text.mean():.0%}")
    b.metric("ผลลัพธ์ที่เปิดข้อความต้นฉบับได้", f"{ok:.0%}", help=f"จากผลค้นทุกอาการ {len(res_ids)} ตำรับ")

    # ---- usability ----
    st.markdown("### 4 · การใช้งาน")
    us = _csv("eval_usability.csv")
    if us is None:
        _missing("ผลทดลองผู้ใช้", "eval_usability.csv", "user, task, seconds, success (1/0), feedback")
    else:
        a, b = st.columns(2)
        a.metric("เวลาเฉลี่ยที่ใช้หา", f"{pd.to_numeric(us['seconds'], errors='coerce').mean():.0f} วินาที")
        b.metric("ทำงานสำเร็จ", f"{(us['success'].str.strip() == '1').mean():.0%}")
        st.dataframe(us[["user", "task", "feedback"]], hide_index=True, width="stretch")

    # ---- gate ----
    st.markdown("### 5 · ทดสอบประตูความพร้อม (3 ตำรับทดสอบ)")
    gt = gate_fixtures.run()
    st.dataframe(gt, hide_index=True, width="stretch")
    if gt["ถูกต้อง"].all():
        st.success("ทุกกรณีถูกต้อง: ผ่านครบ / ไม่ผ่าน 1 ตัว / เกรดไม่ครบ และความเกี่ยวข้องสูงไม่ชนะ gate")
    else:
        st.error("มีกรณีที่ไม่ถูกต้อง")

    # ---- hypotheses ----
    st.markdown("### 6 · คุณภาพสมมติฐาน (หน้า สร้างสมมติฐาน)")
    hy = _csv("eval_hypothesis.csv")
    if hy is None:
        _missing("คะแนนจากผู้เชี่ยวชาญ", "eval_hypothesis.csv",
                 "target, rater, consistency (1-5), evidence_clarity (1-5), worth_study (1-5)")
    else:
        cols = ["consistency", "evidence_clarity", "worth_study"]
        means = hy[cols].apply(pd.to_numeric, errors="coerce").mean()
        c = st.columns(3)
        for col, lab_, v in zip(c, ["สอดคล้องหลักการแพทย์แผนไทย", "ความชัดเจนของหลักฐาน", "น่าศึกษาต่อ"], means):
            col.metric(lab_, f"{v:.1f}/5")
        st.caption("ไม่ใช่หลักฐานความปลอดภัยหรือประสิทธิผล")

    # ---- AI extraction ----
    st.markdown("### 7 · AI สกัดหลักฐาน (ส่วนขยาย)")
    ui.md(ui.MOCK + " ยังไม่ได้สร้าง · ลำดับขั้นที่วางไว้:")
    st.markdown("สมุนไพรที่ยืนยันชื่อวิทย์แล้ว → AI เสนอคำค้น → **PubMed E-utilities** (เก็บ PMID/DOI วันที่ คำค้น) → "
                "AI คัดกรอง → AI สกัดข้อมูล + ข้อความอ้างอิง → ตรวจรูปแบบ (ขาด = ไม่รายงาน) → ตาราง staging (pending) → "
                "**ผู้เชี่ยวชาญตรวจกับบทความจริง** → ตารางหลักฐาน")
    st.caption("ไม่ใช้รายการอ้างอิงจากความจำของโมเดล · ชื่อที่กำกวมต้องผ่านผู้ตรวจ")

    # ---- sensitivity ----
    st.markdown("### 8 · ความไวต่อเกณฑ์")
    sup = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15]
    sens = R.sensitivity(k, "herb_herb", sup, [0.3, 0.5, 0.7])
    fig = go.Figure()
    for conf_, g in sens.groupby("min_confidence"):
        fig.add_trace(go.Scatter(x=g["min_support"], y=g["rules"], mode="lines+markers", name=f"confidence ≥ {conf_}"))
    fig.update_layout(height=300, xaxis_title="min support", yaxis_title="จำนวนกฎ", margin={"l": 0, "r": 0, "t": 10, "b": 0},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")
    st.caption("สมุนไพร↔สมุนไพร · lift ≥ 1 · ไม่รวมตำรับซ้ำ")

    # ---- duplicates ----
    st.markdown("### 9 · ตำรับซ้ำข้ามแหล่ง")
    n_dup = int((rec["duplicate_of"] != "").sum())
    st.metric("ตำรับที่ตัดออก (duplicate_of)", n_dup)
    if n_dup:
        r0, _ = R.cached_rules(k, R.Params())
        r1, _ = R.cached_rules(k, R.Params(include_duplicates=True))
        cmp = r0.head(10)[["antecedent", "consequent", "lift", "count"]].merge(
            r1[["antecedent", "consequent", "lift", "count"]], on=["antecedent", "consequent"], how="left",
            suffixes=(" ไม่รวมซ้ำ", " รวมซ้ำ"))
        st.dataframe(cmp, hide_index=True, width="stretch")
        st.caption("ถ้ารวมตำรับที่คัดลอกกัน กฎจะดูแรงกว่าความจริง")

    # ---- demo case ----
    st.markdown("### 10 · กรณีสาธิต: ปวดข้อ")
    st.caption(f"เกณฑ์กำหนดไว้ก่อนดูผล: อาการ {DEMO_QUERY['symptoms']} · โหมด Industry · ทุกแหล่ง · ไม่ปรับเพื่อให้ได้คำตอบเดิม")
    if "ปวดข้อ" not in k.symptom_terms():
        st.info("ข้อมูลไม่พอ: ยังไม่มีอาการ 'ปวดข้อ' ในฐานข้อมูล")
    else:
        ready, limited = recommend(k, DEMO_QUERY["symptoms"], [], DEMO_QUERY["books"], INDUSTRY,
                                   s["weight_symptom"], s["weight_indication"])
        a, b = st.columns(2)
        a.metric("ผ่านเกณฑ์", len(ready))
        b.metric("มีข้อจำกัด", len(limited))
        manual = _csv("eval_demo_manual.csv")
        if manual is None:
            _missing("รายการตำรับที่ทีมเลือกเองในงานวิจัย acute gout เดิม (อ้างอิงตัวเลขจากบทความต้นฉบับเท่านั้น)",
                     "eval_demo_manual.csv", "recipe_id, source")
        else:
            got = {r.match.recipe_id for r in ready + limited}
            want = set(manual["recipe_id"])
            st.metric("ตำรับที่ทีมเลือกเดิม ที่ระบบพบด้วย", f"{len(got & want)}/{len(want)}")
            st.caption("แหล่ง: " + "; ".join(sorted(set(manual.get("source", pd.Series(dtype=str))) - {""})))
