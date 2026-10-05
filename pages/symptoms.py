import streamlit as st

import ui
from core.safety import all_recipe_levels
from core.search import search_by_symptoms

d = ui.ds()
st.title("ค้นหาจากอาการ")
st.write("เลือกอาการหลัก แล้วเพิ่มอาการร่วมเพื่อให้ผลแม่นขึ้น")

all_symptoms = d.symptoms["symptom"].value_counts()


@st.cache_data(show_spinner=False)
def co_symptoms(fp: str, main: str, top: int = 10) -> list[str]:
    """Symptoms most often listed together with `main` in the same recipe."""
    sym = ui.ds().symptoms
    ids = sym.loc[sym["symptom"] == main, "recipe_id"]
    others = sym[sym["recipe_id"].isin(ids) & (sym["symptom"] != main)]
    return others["symptom"].value_counts().head(top).index.tolist()


with st.container(border=True):
    main = st.selectbox(
        "1. อาการหลัก", all_symptoms.index.tolist(), index=None, key="main_symptom",
        placeholder="พิมพ์หรือเลือกอาการ เช่น ไข้",
        format_func=lambda s: f"{s} ({all_symptoms[s]} ตำรับ)",
    )
    related = co_symptoms(d.fingerprint, main) if main else []
    extra = st.pills("2. อาการร่วม (ไม่บังคับ) · อาการที่มักพบคู่กันในตำรับ", related,
                     selection_mode="multi", key="extra_symptoms") if related else []

selected = ([main] if main else []) + list(extra or [])
if not selected:
    st.caption("เลือกอาการหลักเพื่อเริ่มค้นหา")
    st.stop()

res = search_by_symptoms(d, selected)
st.markdown(f"### พบ {len(res):,} ตำรับที่มีข้อมูลสอดคล้อง")
st.caption("เรียงตามความสอดคล้องกับข้อมูลอาการ")

levels = all_recipe_levels(d)
show = st.session_state.get("show_n", 9)
cols = st.columns(3)
for i, r in enumerate(res.head(show).itertuples(index=False)):
    herbs = d.herbs_of(r.recipe_id)["herb_id"].tolist()
    with cols[i % 3], st.container(border=True):
        st.markdown(
            f'<span class="mono" style="color:#7A5E1C">{ui.esc(r.recipe_id)}</span> {ui.safety_badge(levels.get(r.recipe_id, "none"))}',
            unsafe_allow_html=True,
        )
        st.markdown(f"#### {r.name_th}")
        pct = round(r.score * 100)
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;font-size:.9rem">'
            f'<span>ความสอดคล้องกับข้อมูลอาการ</span><b class="mono">{pct}%</b></div>'
            f'<div class="scorebar"><div style="width:{pct}%"></div></div>',
            unsafe_allow_html=True,
        )
        more = f" +{len(herbs) - 4}" if len(herbs) > 4 else ""
        st.markdown(ui.chips(herbs[:4]) + more, unsafe_allow_html=True)
        book = d.scriptures.set_index("scripture_id")["name_th"].get(r.scripture_id, r.scripture_id)
        st.caption(f"คัมภีร์: {book}")
        if st.button("ดูตำรับ", key=f"open-{r.recipe_id}", width="stretch"):
            ui.open_recipe(r.recipe_id)

if len(res) > show and st.button(f"แสดงเพิ่ม ({len(res) - show:,} ตำรับ)"):
    st.session_state["show_n"] = show + 9
    st.rerun()

st.markdown(
    '<div class="note"><b>ความสอดคล้อง</b> = สัดส่วนอาการที่คุณเลือกซึ่งตรงกับข้อมูลในตำรับ '
    "ไม่ใช่ประสิทธิผลในการรักษา</div>",
    unsafe_allow_html=True,
)
