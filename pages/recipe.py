import plotly.graph_objects as go
import streamlit as st

import ui
from core.safety import recipe_flags

d = ui.ds()
rid = st.session_state.get("recipe_id") or st.query_params.get("id")
ids = d.prescriptions["recipe_id"].tolist()
if rid not in ids:
    rid = st.selectbox("เลือกตำรับ", ids)
st.query_params["id"] = rid

r = d.recipe(rid)
books = d.scriptures.set_index("scripture_id")["name_th"]
herbs = d.herbs_of(rid)
flags = recipe_flags(d, rid)

st.page_link("pages/explore.py", label="← กลับไปสำรวจตำรับ")
st.markdown(f'<span class="mono" style="color:#7A5E1C">ตำรับ #{ui.esc(rid)}</span>', unsafe_allow_html=True)
st.title(r["name_th"])
st.write(f"แหล่งข้อมูล: **{books.get(r['scripture_id'], r['scripture_id'])}**"
         + (f" · รูปแบบ: {r['form']}" if r["form"] else ""))

# Safety first, always visible
flag_lines = ""
if not flags.empty:
    names = ", ".join(flags["herb_id"])
    flag_lines = f"<p style='margin:8px 0 0'><b>ตำรับนี้มีส่วนประกอบที่มีข้อควรระวังด้านความปลอดภัย:</b> {ui.esc(names)}</p>"
st.markdown(
    f'<div class="warnbox"><b>⚠️ ข้อควรระวัง</b><p style="margin:6px 0 0">ข้อมูลนี้เป็นการนำข้อมูลจากตำรับยาโบราณมาจัดโครงสร้าง'
    f"เพื่อการศึกษาและวิจัย ไม่ใช่คำแนะนำในการรักษาโรค</p>{flag_lines}</div>",
    unsafe_allow_html=True,
)
if not flags.empty:
    with st.expander("ดูข้อมูลความปลอดภัย"):
        for f in flags.itertuples(index=False):
            st.markdown(f"{ui.safety_badge(f.safety_level)} **{ui.esc(f.herb_id)}** · {ui.esc(f.safety_note)}",
                        unsafe_allow_html=True)

left, right = st.columns([3, 2], gap="large")
with left:
    st.markdown("### ใช้ในกลุ่มอาการ")
    st.markdown(ui.chips(d.symptoms_of(rid)), unsafe_allow_html=True)

    st.markdown("### ส่วนประกอบ")
    cols = [c for c in ("herb_id", "sci_name", "amount") if c in herbs.columns]
    st.dataframe(
        herbs[cols],
        hide_index=True,
        width="stretch",
        column_config={"herb_id": "สมุนไพร", "sci_name": "ชื่อวิทยาศาสตร์", "amount": "ปริมาณ"},
    )

    with st.expander("📜 ดูข้อความจากคัมภีร์ต้นฉบับ"):
        text = r["original_text"] or "[ยังไม่ได้นำเข้าข้อความต้นฉบับ]"
        st.markdown(f'<div class="interp serif" style="font-size:1.1rem;line-height:1.9">{ui.esc(text)}</div>',
                    unsafe_allow_html=True)
        st.caption(f"{books.get(r['scripture_id'], '')} · {r['page_ref']} · ข้อมูลดิจิทัลอ้างอิงจากต้นฉบับนี้")

with right, st.container(border=True):
    st.markdown("### สมุนไพรเหล่านี้มักปรากฏร่วมกันหรือไม่?")
    p = ui.pairs(d.fingerprint, 1)
    in_recipe = set(herbs["herb_id"])
    sub = p[p["a"].isin(in_recipe) & p["b"].isin(in_recipe)].head(6)
    if sub.empty:
        st.caption("ยังไม่มีข้อมูลคู่สมุนไพรของตำรับนี้")
    else:
        fig = go.Figure(go.Bar(
            x=sub["lift"], y=sub["a"] + " + " + sub["b"], orientation="h",
            marker_color="#1F4D3A", text=sub["lift"].round(2), textposition="outside",
        ))
        fig.add_vline(x=1, line_dash="dash", line_color="#55605A")
        fig.update_layout(height=60 + 44 * len(sub), margin={"l": 0, "r": 30, "t": 0, "b": 0},
                          yaxis={"autorange": "reversed"}, xaxis_title="Lift (1 = เท่าความบังเอิญ)",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        st.caption("Lift = คู่นี้ปรากฏร่วมกันบ่อยกว่าที่คาดจากความบังเอิญกี่เท่า")
        top = sub.iloc[0]
        if st.button("ดูความสัมพันธ์ →", type="primary", width="stretch"):
            st.session_state["pair"] = (top["a"], top["b"])
            st.switch_page("pages/statistics.py")
