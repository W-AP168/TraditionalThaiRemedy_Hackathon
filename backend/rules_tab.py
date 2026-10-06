"""Back-end · กฎความสัมพันธ์: full rules table, thresholds, network, export, permutation test."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from core import rules as R
from core.data import BOOKS
from core.network import build_graph, figure
from core.statistics import permutation_test


def render() -> None:
    k = ui.kb()
    with st.form("rules"):
        a, b, c = st.columns(3)
        analysis = a.selectbox("ชนิดการวิเคราะห์", list(R.ANALYSES), format_func=R.ANALYSES.get)
        books = b.multiselect("แหล่ง", list(BOOKS), default=list(BOOKS), format_func=ui.book_label)
        dup = c.checkbox("รวมตำรับที่ซ้ำกับแหล่งอื่น", value=False)
        a, b, c, d = st.columns(4)
        sup = a.slider("min support", 0.01, 0.30, R.Params.min_support, 0.01)
        conf = b.slider("min confidence", 0.05, 1.0, R.Params.min_confidence, 0.05)
        lift = c.slider("min lift", 1.0, 5.0, R.Params.min_lift, 0.1)
        mlen = d.selectbox("ขนาดกลุ่มสูงสุด", [2, 3, 4], index=1)
        st.form_submit_button("คำนวณ (แคชผลไว้)", type="primary")
    p = R.Params(analysis=analysis, min_support=sup, min_confidence=conf, min_lift=lift, books=tuple(books),
                 include_duplicates=dup, max_len=mlen)
    rules, meta = ui.get_rules(p)
    ui.md(ui.data_badge(k))
    st.caption(ui.rules_meta(meta))
    if meta.get("note"):
        st.warning(meta["note"])
    ui.rules_disclaimer()
    st.metric("กฎที่ผ่านเกณฑ์", f"{len(rules):,}", help=f"ข้อมูลน้อย (< {meta['low_count']} ตำรับ): "
              f"{int(rules['low_data'].sum()) if len(rules) else 0}")
    show = rules.drop(columns=["antecedent_items", "consequent_items"]).assign(
        low_data=lambda d: d["low_data"].map({True: "ข้อมูลน้อย", False: ""}))
    st.dataframe(show, hide_index=True, width="stretch", column_config={
        "antecedent": "ถ้ามี (X)", "consequent": "มักพบ (Y)", "count": "จำนวนตำรับจริง",
        "support": st.column_config.NumberColumn(format="%.3f"),
        "confidence": st.column_config.NumberColumn(format="%.2f"),
        "lift": st.column_config.NumberColumn(format="%.2f"), "low_data": ""})
    header = "# " + ui.rules_meta(meta) + "\n"
    st.download_button("ดาวน์โหลด CSV (มี metadata บรรทัดแรก)",
                       (header + show.to_csv(index=False)).encode("utf-8-sig"),
                       file_name=f"rules_{analysis}_v{k.version}.csv", mime="text/csv")

    if analysis == "herb_herb" and len(rules):
        st.markdown("### เครือข่ายสมุนไพร")
        pairs = rules[(rules["antecedent_items"].map(len) == 1) & (rules["consequent_items"].map(len) == 1)]
        pairs = pairs.assign(a=pairs["antecedent_items"].str[0], b=pairs["consequent_items"].str[0])
        pairs = pairs[pairs["a"] < pairs["b"]]
        counts = k.items["item"].value_counts()
        st.plotly_chart(figure(build_graph(pairs, counts, min_lift=lift, top=60)), width="stretch")
        st.caption("วงกลม = สมุนไพร (ขนาด = จำนวนตำรับ) · เส้นหนา = lift สูง")

    st.markdown("### หลักฐานเพิ่มเติม: permutation test ของ lift")
    st.caption("สุ่มสลับสมุนไพร B ข้ามตำรับ 1,000 รอบ (คงจำนวนตำรับที่ใช้ A และ B) แล้วดูว่าการสุ่มได้ lift สูงเท่าค่าจริงบ่อยแค่ไหน")
    X = R.transactions(k, R.Params(books=tuple(books), include_duplicates=dup))
    if X.empty:
        st.info("ข้อมูลไม่พอ")
        return
    X.columns = [R.label(c) for c in X.columns]
    herbs = X.sum().sort_values(ascending=False).index.tolist()
    a, b = st.columns(2)
    ha = a.selectbox("สมุนไพร A", herbs, index=herbs.index("ขิง") if "ขิง" in herbs else 0)
    hb = b.selectbox("สมุนไพร B", [h for h in herbs if h != ha],
                     index=([h for h in herbs if h != ha].index("ดีปลี") if "ดีปลี" in herbs and ha != "ดีปลี" else 0))
    t = permutation_test(X, ha, hb, n_perm=1000)
    m = st.columns(4)
    m[0].metric("lift จริง", f"{t['observed_lift']:.2f}")
    m[1].metric("lift เฉลี่ยจากการสุ่ม", f"{t['null_mean']:.2f}")
    m[2].metric("p (permutation)", f"{t['p_value']:.3f}")
    m[3].metric("ตำรับที่มีทั้งคู่", t["count"])
    fig = go.Figure(go.Histogram(x=np.asarray(t["null_lift"]), nbinsx=30, marker_color="#C9D3CC"))
    fig.add_vline(x=t["observed_lift"], line_color="#16302A", line_width=3, annotation_text="ค่าจริง")
    fig.update_layout(height=260, margin={"l": 0, "r": 0, "t": 20, "b": 0}, xaxis_title="lift", yaxis_title="รอบ",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"ธุรกรรม {t['n']} ตำรับ · ข้อมูล v{k.version} · ไม่ยืนยันเหตุและผลหรือฤทธิ์เสริมกัน")
