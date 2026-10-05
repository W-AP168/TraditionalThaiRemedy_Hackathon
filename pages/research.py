import streamlit as st

import ui
from core.network import build_graph, figure

if not ui.lab_gate():
    st.stop()

d = ui.ds()
st.caption("RESEARCH DASHBOARD")
st.title("ภาพรวมฐานความรู้")
st.caption(ui.dataset_caption())
ui.sample_banner()

tests = ui.pair_tests(d.fingerprint)
n_sig = int((tests["q_value"] < 0.05).sum())

c = st.columns(4)
c[0].metric("ตำรับ", f"{d.n_recipes:,}")
c[1].metric("สมุนไพร (หลังรวมชื่อพ้อง)", f"{d.n_herbs:,}")
c[2].metric("คัมภีร์", d.n_scriptures)
c[3].metric("คู่ที่ผ่าน permutation test", n_sig, help=f"FDR q < 0.05 จาก {len(tests)} คู่ที่ทดสอบ")

left, right = st.columns([3, 2], gap="large")
with left, st.container(border=True):
    st.markdown("### Knowledge Network")
    counts = d.ingredients["herb_id"].value_counts()
    g = build_graph(ui.pairs(d.fingerprint, 3), counts, min_lift=1.5, top=40)
    st.plotly_chart(figure(g), width="stretch")
    st.caption("วงกลม = สมุนไพร · ขนาด = จำนวนตำรับ · เส้นหนา = Lift สูง")

with right, st.container(border=True):
    st.markdown("### คู่ที่เด่นที่สุด")
    top = tests.sort_values("observed_lift", ascending=False).query("q_value < 0.05").head(8)
    for r in top.itertuples(index=False):
        a, b = st.columns([3, 1])
        if a.button(f"{r.a} ↔ {r.b}", key=f"pair-{r.a}-{r.b}", width="stretch"):
            st.session_state["pair"] = (r.a, r.b)
            st.switch_page("pages/statistics.py")
        b.markdown(f'<div class="mono" style="padding-top:8px">{r.observed_lift:.2f}</div>', unsafe_allow_html=True)
    st.caption("ตัวเลข = Lift · เฉพาะคู่ที่ q < 0.05")
    st.page_link("pages/apriori_lab.py", label="เปิด Apriori Lab →")
