import streamlit as st

import ui
from core.network import build_graph, figure, neighbors
from core.search import symptoms_for_herb, symptoms_for_pair

if not ui.lab_gate():
    st.stop()

d = ui.ds()
st.title("Knowledge Graph")
st.write("เลือกสมุนไพรเพื่อดูว่าใช้กับอาการใด และมักปรากฏร่วมกับอะไร")

counts = d.ingredients["herb_id"].value_counts()
c1, c2, c3 = st.columns([2, 1, 1])
min_lift = c2.slider("Lift ขั้นต่ำ", 1.0, 4.0, 1.5, 0.1)
top = c3.slider("จำนวนเส้นสูงสุด", 10, 120, 50, 10)
g = build_graph(ui.pairs(d.fingerprint, 3), counts, min_lift=min_lift, top=top)
nodes = sorted(g.nodes, key=lambda n: -counts.get(n, 0))
if not nodes:
    st.warning("ไม่มีคู่ที่ผ่านเกณฑ์ ลองลด Lift ขั้นต่ำ")
    st.stop()
default = st.session_state.get("herb_id")
herb = c1.selectbox("สมุนไพร", nodes, index=nodes.index(default) if default in nodes else 0)
st.session_state["herb_id"] = herb

left, right = st.columns([3, 2], gap="large")
with left, st.container(border=True):
    st.plotly_chart(figure(g, highlight=herb), width="stretch")
    st.caption("วงกลม = สมุนไพร (ขนาด = จำนวนตำรับ) · เส้นหนา = Lift สูง · สีทอง = คู่ของสมุนไพรที่เลือก")

with right, st.container(border=True):
    st.caption("WHY THIS HERB?")
    st.markdown(f"## {herb}")
    st.metric("ปรากฏใน", f"{counts[herb]} ตำรับ")
    st.markdown("**กลุ่มอาการ**")
    st.markdown(ui.chips(symptoms_for_herb(d, herb).index, gold=True), unsafe_allow_html=True)
    nb = neighbors(g, herb)
    st.markdown(f"**พบว่า{herb}มักปรากฏร่วมกับ…**")
    for r in nb.head(6).itertuples(index=False):
        if st.button(f"{herb} + {r.herb}   ·   Lift {r.lift:.2f}", key=f"nb-{r.herb}", width="stretch"):
            st.session_state["graph_pair"] = (herb, r.herb)
    gp = st.session_state.get("graph_pair")
    if gp and gp[0] == herb:
        recipes, sym = symptoms_for_pair(d, *gp)
        st.markdown(
            f'<div style="background:#16302A;color:#F7F3EA;border-radius:14px;padding:16px">'
            f"<b>{ui.esc(gp[0])} + {ui.esc(gp[1])}</b><br>พบร่วมกันใน <b style='color:#E2C27A'>{len(recipes)}</b> ตำรับ<br>"
            f"เกี่ยวข้องกับ: {ui.esc(' · '.join(sym.index))}</div>",
            unsafe_allow_html=True,
        )
        if st.button("ดูหลักฐานทางสถิติ →", width="stretch"):
            st.session_state["pair"] = gp
            st.switch_page("pages/statistics.py")
