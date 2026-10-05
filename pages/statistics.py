import numpy as np
import plotly.graph_objects as go
import streamlit as st

import ui
from core.statistics import interpret

if not ui.lab_gate():
    st.stop()

d = ui.ds()
tests = ui.pair_tests(d.fingerprint)
st.caption("STATISTICAL EVIDENCE")

options = list(zip(tests["a"], tests["b"]))
want = st.session_state.get("pair")
if want and want not in options and tuple(reversed(want)) in options:
    want = tuple(reversed(want))
choices = options if want in options or not want else [want] + options
pair = st.selectbox("คู่สมุนไพร", choices, index=choices.index(want) if want in choices else 0,
                    format_func=lambda p: f"{p[0]} ↔ {p[1]}")
st.session_state["pair"] = pair
a, b = pair

t = ui.one_test(d.fingerprint, a, b)
row = tests[(tests["a"] == a) & (tests["b"] == b)]
q = float(row["q_value"].iloc[0]) if not row.empty else None

st.title(f"{a} ↔ {b}")
st.write("คู่นี้แรงกว่าที่คาดจากความบังเอิญหรือไม่?")

left, right = st.columns(2, gap="large")
with left, st.container(border=True):
    st.markdown("### Lift ที่สังเกตได้ เทียบกับค่าจากการสุ่ม")
    fig = go.Figure(go.Bar(
        x=[t["observed_lift"], t["null_mean"]], y=["Observed Lift", "Randomized mean"], orientation="h",
        marker_color=["#16302A", "#A9B8AE"], text=[f"{t['observed_lift']:.2f}", f"{t['null_mean']:.2f}"],
        textposition="outside",
    ))
    fig.update_layout(height=180, margin={"l": 0, "r": 40, "t": 0, "b": 0}, yaxis={"autorange": "reversed"},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_title="Lift",
                      xaxis_range=[0, max(t["observed_lift"], t["null_mean"]) * 1.2])
    st.plotly_chart(fig, width="stretch")
    m = st.columns(3)
    m[0].metric("Permutation (รอบ)", f"{t['n_perm']:,}")
    m[1].metric("p-value", f"{t['p_value']:.3f}")
    m[2].metric("FDR q-value", f"{q:.3f}" if q is not None else "—", help="ปรับ multiple testing (Benjamini–Hochberg)")
    sig = (q if q is not None else t["p_value"]) < 0.05
    if sig:
        st.success("✓ statistically unusual under the permutation model")
    else:
        st.warning("ยังไม่ต่างจากความบังเอิญอย่างมีนัยสำคัญ")
    st.caption(f"พบร่วมกันใน {t['count']} ตำรับ · {a} {t['count_a']} ตำรับ · {b} {t['count_b']} ตำรับ · จาก {t['n']} ตำรับ")

with right, st.container(border=True):
    st.markdown("### Permutation distribution")
    null = np.asarray(t["null_lift"])
    hist = go.Figure(go.Histogram(x=null, nbinsx=30, marker_color="#C9D3CC", name="จากการสุ่ม"))
    hist.add_vline(x=t["observed_lift"], line_color="#16302A", line_width=3,
                   annotation_text=f"ค่าจริง {t['observed_lift']:.2f}", annotation_position="top left")
    hist.add_vline(x=t["null_mean"], line_dash="dash", line_color="#55605A",
                   annotation_text=f"ค่าเฉลี่ยสุ่ม {t['null_mean']:.2f}", annotation_position="top right")
    hist.update_layout(height=300, margin={"l": 0, "r": 0, "t": 30, "b": 0}, showlegend=False,
                       xaxis_title="Lift", yaxis_title="จำนวนรอบ",
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(hist, width="stretch")
    k = int((null >= t["observed_lift"] - 1e-12).sum())
    st.caption(f"มี {k} ใน {t['n_perm']:,} รอบที่การสุ่มได้ Lift สูงเท่าหรือมากกว่าค่าจริง")

with st.expander("ทำไมถึงถือว่ามีนัยสำคัญ?", expanded=True):
    st.write(
        "เราสุ่มจัดสมุนไพรใหม่ภายในชุดตำรับหลายครั้งเพื่อสร้าง distribution ของค่า Lift ที่คาดว่าจะเกิดจากโครงสร้าง"
        "ข้อมูลแบบสุ่ม จากนั้นเปรียบเทียบค่า Lift ที่สังเกตได้กับ distribution ดังกล่าว"
    )
    st.caption("วิธีสุ่ม: สลับคอลัมน์ของสมุนไพร B ข้ามตำรับ (คงจำนวนตำรับที่ใช้ A และ B ไว้เท่าเดิม) · "
               "p = (1 + จำนวนรอบที่ ≥ ค่าจริง) / (1 + จำนวนรอบ)")
    st.markdown("Prescription → Binary matrix → Apriori → Association rules → Permutation testing → **Statistical evidence**")

st.markdown(
    f'<div class="interp"><b>Interpretation</b><br>{ui.esc(a)}และ{ui.esc(b)}{interpret(t["p_value"], q)}<br><br>'
    "<i>Statistically enriched association observed in historical prescriptions</i> — "
    "ไม่ได้พิสูจน์ประสิทธิผลทางคลินิกหรือเหตุและผล</div>",
    unsafe_allow_html=True,
)

st.markdown("### ทุกคู่ที่ทดสอบ")
st.dataframe(
    tests,
    hide_index=True,
    width="stretch",
    column_config={
        "a": "สมุนไพร A", "b": "สมุนไพร B",
        "count": st.column_config.NumberColumn("ตำรับ", format="%d"),
        "observed_lift": st.column_config.NumberColumn("Lift จริง", format="%.2f"),
        "null_mean": st.column_config.NumberColumn("Lift สุ่มเฉลี่ย", format="%.2f"),
        "p_value": st.column_config.NumberColumn("p", format="%.3f"),
        "q_value": st.column_config.NumberColumn("q (FDR)", format="%.3f"),
    },
)
