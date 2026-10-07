import pandas as pd
import streamlit as st

import ui
from core import rules as R

HYPO = "สมมติฐานเพื่อการวิจัย — ต้องประเมินโดยผู้เชี่ยวชาญ"

k = ui.header("สร้างสมมติฐาน", "Discover · ชุดสมุนไพรจากรูปแบบที่ค้นพบ (ขอบเขตจำกัด)")
ui.md(f'<div class="hypo">{HYPO}</div>')
st.caption("ไม่มีขนาดยา ไม่มีวิธีใช้ ไม่ใช่สูตรยาที่พร้อมใช้")

with st.container(border=True):
    c1, c2 = st.columns(2)
    target_s = c1.multiselect("กลุ่มอาการเป้าหมาย", k.symptom_terms(), key="dis_sym")
    target_i = c2.multiselect("ข้อบ่งใช้เป้าหมาย", k.indication_terms(), key="dis_ind")
    c3, c4, c5 = st.columns(3)
    min_count = c3.number_input("จำนวนตำรับสนับสนุนขั้นต่ำต่อกฎ", 1, 50, int(ui.conf()["low_support_count"]))
    min_lift = c4.slider("Lift ขั้นต่ำ", 1.0, 5.0, 1.5, 0.1)
    max_herbs = c5.slider("จำนวนสมุนไพรสูงสุด", 2, 12, 6)

if not target_s and not target_i:
    st.info("เลือกอาการหรือข้อบ่งใช้เป้าหมาย")
    ui.footer()
    st.stop()

used = []
for analysis, targets in (("symptom_herb", set(target_s)), ("indication_herb", set(target_i))):
    if not targets:
        continue
    rules, meta = ui.get_rules(R.DEFAULTS[analysis])
    st.caption(ui.rules_meta(meta))
    if rules.empty:
        continue
    keep = rules[rules["antecedent_items"].map(lambda a: set(a) <= targets)
                 & (rules["count"] >= min_count) & (rules["lift"] >= min_lift)]
    used.append(keep.assign(analysis=R.ANALYSES[analysis]))
rules_used = pd.concat(used, ignore_index=True) if used else pd.DataFrame()

if rules_used.empty:
    st.warning("ข้อมูลไม่พอ: ไม่มีกฎที่ตรงเป้าหมายและมีตำรับสนับสนุนเพียงพอ ลองลดเกณฑ์ หรือรอข้อมูลเพิ่ม")
    ui.rules_disclaimer()
    ui.footer()
    st.stop()

cand = (rules_used.explode("consequent_items")
        .groupby("consequent_items")
        .agg(lift_max=("lift", "max"), rules=("lift", "size"), count_max=("count", "max"))
        .sort_values(["lift_max", "count_max"], ascending=False).head(max_herbs).reset_index()
        .rename(columns={"consequent_items": "herb"}))

st.markdown("### ชุดสมุนไพรที่เสนอ")
herb_tbl = k.t["herbs"].set_index("herb_id")
for h in cand.to_dict("records"):
    hid = h["herb"] if h["herb"] in herb_tbl.index else ""
    ctx = []
    if hid:
        for col, lab in (("taste", "รสยา"), ("pikat", "พิกัดยา")):
            if herb_tbl.at[hid, col]:
                ctx.append(f"{lab}: {herb_tbl.at[hid, col]}")
    with st.container(border=True):
        ui.md(f"**{ui.esc(h['herb'])}** {ui.herb_badges(k, hid)} · lift สูงสุด {h['lift_max']:.2f} · "
              f"{h['rules']} กฎ · สูงสุด {h['count_max']} ตำรับ"
              + (f"<br><small>{ui.esc(' · '.join(ctx))}</small>" if ctx else
                 "<br><small>รสยา/พิกัดยา: ยังไม่มีข้อมูล</small>"))
        if hid:
            ui.md(ui.safety_html(k, hid))

st.markdown("### ตำรับต้นทาง")
herbset = set(cand["herb"])
sym = k.t["recipe_symptoms"]
ind = k.t["recipe_indications"]
hit = set(sym.loc[sym["symptom_original"].isin(target_s), "recipe_id"]) | \
      set(ind.loc[ind["indication"].isin(target_i), "recipe_id"])
src = (k.items[k.items["recipe_id"].isin(hit) & k.items["item"].isin(herbset)]
       .groupby("recipe_id")["item"].agg(lambda s: ", ".join(sorted(set(s)))).rename("สมุนไพรที่ตรงชุด").reset_index())
src["จำนวน"] = src["สมุนไพรที่ตรงชุด"].str.count(",") + 1
src = src.sort_values("จำนวน", ascending=False)
st.dataframe(src, hide_index=True, width="stretch")

st.markdown("### กฎที่ใช้")
st.dataframe(rules_used[["analysis", "antecedent", "consequent", "count", "support", "confidence", "lift"]],
             hide_index=True, width="stretch",
             column_config={"count": "จำนวนตำรับ", "lift": st.column_config.NumberColumn(format="%.2f"),
                            "confidence": st.column_config.NumberColumn(format="%.2f"),
                            "support": st.column_config.NumberColumn(format="%.3f")})
ui.rules_disclaimer()
ui.md(f'<div class="hypo">{HYPO}</div>')
ui.footer()
