import streamlit as st

import ui
from core.safety import LEVEL_LABEL, all_recipe_levels
from core.search import search_recipes

d = ui.ds()
st.title("สำรวจตำรับ")
st.caption(f"ตำรับทั้งหมดจาก {d.n_scriptures} คัมภีร์ · {ui.dataset_caption()}")

c1, c2 = st.columns([2, 1])
q = c1.text_input("ค้นหา", placeholder="ชื่อตำรับ, รหัส หรือชื่อสมุนไพร เช่น ดีปลี", label_visibility="collapsed")
books = dict(zip(d.scriptures["scripture_id"], d.scriptures["name_th"]))
picked = c2.multiselect("คัมภีร์", list(books), format_func=lambda k: f"{k} · {books[k]}",
                        placeholder="ทุกคัมภีร์", label_visibility="collapsed")

res = search_recipes(d, q, picked)
levels = all_recipe_levels(d)
table = res.assign(
    safety=res["recipe_id"].map(levels).map(lambda lv: LEVEL_LABEL[lv] if lv != "none" else ""),
    scripture=res["scripture_id"].map(books),
)[["recipe_id", "name_th", "scripture", "form", "n_herbs", "safety"]]

st.caption(f"พบ {len(table):,} ตำรับ · คลิกแถวเพื่อดูรายละเอียด")
event = st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "recipe_id": "รหัส",
        "name_th": "ตำรับ",
        "scripture": "คัมภีร์",
        "form": "รูปแบบ",
        "n_herbs": st.column_config.NumberColumn("สมุนไพร", format="%d"),
        "safety": "ความปลอดภัย",
    },
)
if event.selection.rows:
    ui.open_recipe(table.iloc[event.selection.rows[0]]["recipe_id"])
