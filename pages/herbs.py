import streamlit as st

import ui
from core.network import build_graph, figure, neighbors
from core.search import recipes_with_herb, symptoms_for_herb, symptoms_for_pair

d = ui.ds()
st.title("คลังสมุนไพร")
st.write("เลือกสมุนไพรเพื่อดูว่าใช้กับอาการใด และมักปรากฏร่วมกับอะไร")

counts = d.ingredients["herb_id"].value_counts()
herb_list = counts.index.tolist()
default = st.session_state.get("herb_id")
herb = st.selectbox("สมุนไพร", herb_list, index=herb_list.index(default) if default in herb_list else 0,
                    format_func=lambda h: f"{h} ({counts[h]} ตำรับ)")
st.session_state["herb_id"] = herb

info = d.herbs.set_index("herb_id")
row = info.loc[herb] if herb in info.index else None
pairs = ui.pairs(d.fingerprint, 3)
g = build_graph(pairs, counts, min_lift=1.0, top=80)
nb = neighbors(g, herb)

left, right = st.columns([2, 3], gap="large")
with left:
    st.markdown(f"## {herb}")
    if row is not None:
        st.markdown(f"*{row['sci_name']}* {ui.safety_badge(row['safety_level'])}", unsafe_allow_html=True)
        if row["safety_note"]:
            st.caption(f"⚠️ {row['safety_note']}")
        syns = d.synonyms.loc[d.synonyms["herb_id"] == herb, "synonym"].tolist()
        if syns:
            st.caption("ชื่อพ้องในคัมภีร์: " + ", ".join(syns))
    st.metric("ปรากฏใน", f"{counts[herb]} ตำรับ")
    st.markdown("**กลุ่มอาการ**")
    st.markdown(ui.chips(symptoms_for_herb(d, herb).index, gold=True), unsafe_allow_html=True)

    st.markdown(f"**พบว่า{herb}มักปรากฏร่วมกับ…**")
    if nb.empty:
        st.caption("ยังไม่พบคู่ที่เด่น")
    else:
        choice = st.radio(
            "คู่สมุนไพร", nb["herb"].head(6).tolist(), label_visibility="collapsed",
            format_func=lambda h: f"{h}   ·   Lift {nb.set_index('herb').loc[h, 'lift']:.2f}",
        )
        recipes, sym = symptoms_for_pair(d, herb, choice)
        with st.container(border=True):
            st.markdown(f"**{herb} + {choice}**")
            st.write(f"พบร่วมกันใน **{len(recipes)}** ตำรับ")
            st.markdown("เกี่ยวข้องกับ: " + ui.chips(sym.index, gold=True), unsafe_allow_html=True)
            if st.button("ดูหลักฐานทางสถิติ →", width="stretch"):
                st.session_state["pair"] = (herb, choice)
                st.switch_page("pages/statistics.py")

with right:
    st.plotly_chart(figure(g, highlight=herb), width="stretch")
    st.caption("วงกลม = สมุนไพร (ขนาด = จำนวนตำรับ) · เส้นหนา = Lift สูง · สีทอง = คู่ของสมุนไพรที่เลือก")
    with st.expander(f"ตำรับที่มี{herb}"):
        rec = recipes_with_herb(d, herb)[["recipe_id", "name_th", "scripture_id"]]
        ev = st.dataframe(rec, hide_index=True, width="stretch", on_select="rerun",
                          selection_mode="single-row",
                          column_config={"recipe_id": "รหัส", "name_th": "ตำรับ", "scripture_id": "คัมภีร์"})
        if ev.selection.rows:
            ui.open_recipe(rec.iloc[ev.selection.rows[0]]["recipe_id"])
