import streamlit as st

import ui
from core.apriori import SYMPTOM_PREFIX
from core.statistics import interpret

if not ui.lab_gate():
    st.stop()

d = ui.ds()
st.title("Apriori Lab")

with st.sidebar:
    st.markdown("**ANALYSIS SETTINGS**")
    with st.form("settings"):
        kind = st.radio("ประเภทกฎ", ["herb", "symptom", "all"],
                        format_func={"herb": "สมุนไพร ↔ สมุนไพร", "symptom": "อาการ → สมุนไพร",
                                     "all": "ทั้งหมด"}.get)
        sup = st.slider("Minimum Support", 1, 20, 5, format="%d%%", help="พบในอย่างน้อยกี่ % ของตำรับ")
        conf = st.slider("Minimum Confidence", 10, 95, 60, step=5, format="%d%%", help="มี A แล้วมี B ด้วยกี่ %")
        lift = st.slider("Minimum Lift", 1.0, 5.0, 1.5, step=0.1, help="มากกว่า 1 = คู่กันบ่อยกว่าความบังเอิญ")
        st.form_submit_button("RUN ANALYSIS", type="primary", width="stretch")
    st.caption("ผลถูกแคชไว้ต่อชุดค่า รันใหม่เฉพาะเมื่อค่าหรือข้อมูลเปลี่ยน")

rules = ui.rules(d.fingerprint, kind, sup / 100, conf / 100, lift)
st.caption(f"ผ่านเกณฑ์ **{len(rules):,}** กฎ · จาก {d.n_recipes:,} ตำรับ · {ui.dataset_caption()}")

if rules.empty:
    st.warning("ไม่มีกฎที่ผ่านเกณฑ์นี้ ลองลดค่า Support หรือ Lift")
    st.stop()


def label(s: str) -> str:
    return s.replace(SYMPTOM_PREFIX, "อาการ ")


st.markdown("## Strongest association")
# prefer a one-to-one pair: it can be permutation-tested and is easiest to explain
singles = rules[rules["antecedent_set"].map(len) == 1]
top = singles.iloc[0] if not singles.empty else rules.iloc[0]
pairwise = kind == "herb" and len(top["antecedent_set"]) == 1
test = ui.one_test(d.fingerprint, top["antecedent"], top["consequent"]) if pairwise else None

with st.container(border=True):
    a, b = st.columns([1, 2], gap="large")
    p_text = f" · p = {test['p_value']:.3f}" if test else ""
    a.markdown(
        f'<div class="assoc"><span class="herb">{ui.esc(label(top["antecedent"]))}</span><span class="stem"></span>'
        f'<span class="val">Lift {top["lift"]:.2f}{p_text}</span><span class="stem"></span>'
        f'<span class="herb">{ui.esc(label(top["consequent"]))}</span></div>',
        unsafe_allow_html=True,
    )
    with b:
        m = st.columns(4 if test else 3)
        m[0].metric("Support", f"{top['support']:.1%}", help=f"{top['count']} / {top['n']} ตำรับ")
        m[1].metric("Confidence", f"{top['confidence']:.1%}")
        m[2].metric("Lift", f"{top['lift']:.2f}")
        if test:
            m[3].metric("Permutation p", f"{test['p_value']:.3f}")
            st.markdown(
                f'<div class="interp"><b>Interpretation</b><br>{ui.esc(top["antecedent"])}และ{ui.esc(top["consequent"])}'
                f"{interpret(test['p_value'])}</div>",
                unsafe_allow_html=True,
            )
            if st.button("ดูหลักฐานทางสถิติ →"):
                st.session_state["pair"] = (top["antecedent"], top["consequent"])
                st.switch_page("pages/statistics.py")

st.markdown("## กฎทั้งหมด")
table = rules.assign(antecedent=rules["antecedent"].map(label), consequent=rules["consequent"].map(label))
st.dataframe(
    table[["antecedent", "consequent", "count", "support", "confidence", "lift"]],
    hide_index=True,
    width="stretch",
    column_config={
        "antecedent": "ถ้ามี (A)",
        "consequent": "มักพบ (B)",
        "count": st.column_config.NumberColumn("ตำรับ", format="%d"),
        "support": st.column_config.NumberColumn("Support", format="percent"),
        "confidence": st.column_config.NumberColumn("Confidence", format="percent"),
        "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
    },
)
st.download_button("ดาวน์โหลด CSV", table.drop(columns="antecedent_set").to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"rules_{kind}_s{sup}_c{conf}_l{lift}.csv", mime="text/csv")
