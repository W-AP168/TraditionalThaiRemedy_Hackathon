import pandas as pd
import streamlit as st

import ui
from core import rules as R
from core.similarity import compare, similar

k = ui.header("วิเคราะห์ตำรับ", "Analyze · แยก ข้อความตามตำรา / รูปแบบจากฐานข้อมูล / หลักฐานวิจัย")

rec = k.recipes
ids = rec["recipe_id"].tolist()
names = dict(zip(rec["recipe_id"], rec["name"]))
want = st.session_state.get("analyze_id") or st.query_params.get("id")
rid = st.selectbox("ตำรับ", ids, index=ids.index(want) if want in ids else 0,
                   format_func=lambda r: f"{r} · {names.get(r) or ''}")
st.session_state["analyze_id"] = rid
st.query_params["id"] = rid
r = k.recipe(rid)
herbs = k.herbs_of(rid)

# ---------------- 1. text ----------------
st.markdown("## 1 · ข้อความตามตำรา")
with st.container(border=True):
    st.markdown(f"**{ui.esc(r['name'] or rid)}** · {ui.book_label(r['book'])}"
                + (f" · ⚠️ ซ้ำกับ {r['duplicate_of']}" if r["duplicate_of"] else ""))
    ui.md(f"สถานะตรวจสอบ: <span class='badge {'b-ok' if r['review_status'] == 'verified' else 'b-pending'}'>"
          f"{'ยืนยันแล้ว' if r['review_status'] == 'verified' else 'รอตรวจสอบ'}</span>")
    with st.expander("ข้อความต้นฉบับ", expanded=True):
        st.write(r["original_text"] or "ยังไม่มีข้อความต้นฉบับ")
    a, b = st.columns(2)
    a.markdown(f"**สรรพคุณตามตำรา:** {r['indication_text'] or '-'}")
    inds = k.indications_of(rid)
    a.markdown("**ข้อบ่งใช้:** " + (", ".join(inds) if inds else "ยังไม่มีข้อมูลข้อบ่งใช้แยก"))
    sy = k.symptoms_of(rid)
    sy_txt = [f"{o} → {m}" if m else o for o, m in zip(sy["symptom_original"], sy["symptom_modern"])]
    a.markdown("**อาการ:** " + (", ".join(sy_txt) if sy_txt else "-"))
    a.caption("คำโบราณ ≠ การวินิจฉัยสมัยใหม่ คำที่เทียบแล้ว (→) ต้องมีเหตุผลและผู้ตรวจ")
    b.markdown(f"**วิธีทำ:** {r['preparation'] or '-'}  \n**กระสายยา:** {r['vehicle'] or '-'}  \n"
               f"**รูปแบบยา:** {r['dosage_form'] or '-'}  \n**วิธีใช้:** {r['usage'] or '-'}")

    st.markdown("**ส่วนประกอบ**")
    if herbs.empty:
        st.warning("ข้อมูลไม่พอ: ตำรับนี้ยังไม่ได้แยกสมุนไพร")
    else:
        rows = []
        pending = '<span class="badge b-pending">รอตรวจสอบ</span>'
        for h in herbs.to_dict("records"):
            pct = f"{h['qty_percent']}%" if h["qty_percent"] else "-"
            std = ui.esc(k.herb_name(h["herb_id"])) if h["herb_id"] else pending
            grp = f" <small>(จาก{ui.esc(h['from_group'])})</small>" if h["from_group"] else ""
            qty = ui.esc((h["qty_original"] + " " + h["unit_original"]).strip() or "-")
            rows.append(f"<tr><td>{ui.esc(h['herb_name_original'])}</td><td>{std}{grp}</td>"
                        f"<td>{ui.esc(h['part_used'] or '-')}</td><td>{qty}</td>"
                        f"<td title='{ui.esc(h['qty_rule'])}'>{pct}</td><td>{ui.herb_badges(k, h['herb_id'])}</td></tr>")
        ui.md("<div style='overflow-x:auto'><table style='width:100%'><tr><th>ชื่อตามตำรา</th><th>ชื่อมาตรฐาน</th>"
              "<th>ส่วนที่ใช้</th><th>ปริมาณ (ต้นฉบับ)</th><th>%</th><th>เกรด</th></tr>" + "".join(rows) + "</table></div>")
        st.caption("% คำนวณเฉพาะตำรับที่ทุกตัวใช้หน่วยเดียวกัน (วางเมาส์ดูวิธีคำนวณ) หน่วยโบราณต่างชนิดยังไม่แปลง")
        ui.grade_legend()
        for hid in herbs["herb_id"].unique():
            if hid:
                ui.md(ui.safety_html(k, hid))

# ---------------- 2. database patterns ----------------
st.markdown("## 2 · รูปแบบจากฐานข้อมูล")
with st.container(border=True):
    rules, meta = ui.get_rules(R.DEFAULTS["herb_herb"])
    hs = k.herb_set(rid)
    inside = rules[[set(a) | set(c) <= hs for a, c in zip(rules["antecedent_items"], rules["consequent_items"])]] \
        if not rules.empty else rules
    st.markdown("**คู่/กลุ่มสมุนไพรในตำรับนี้ที่พบเป็นกฎในฐานข้อมูล**")
    st.caption(ui.rules_meta(meta))
    if inside.empty:
        st.info("ไม่พบกฎที่สมุนไพรทั้งหมดอยู่ในตำรับนี้ (ที่เกณฑ์ปัจจุบัน)")
    else:
        show = inside.assign(**{"ข้อมูลน้อย": inside["low_data"].map({True: "ข้อมูลน้อย", False: ""})})
        st.dataframe(show[["antecedent", "consequent", "count", "support", "confidence", "lift", "ข้อมูลน้อย"]],
                     hide_index=True, width="stretch", column_config={
                         "antecedent": "ถ้ามี", "consequent": "มักพบ", "count": "จำนวนตำรับ",
                         "support": st.column_config.NumberColumn(format="%.3f"),
                         "confidence": st.column_config.NumberColumn(format="%.2f"),
                         "lift": st.column_config.NumberColumn(format="%.2f")})
    ui.rules_disclaimer()

    st.markdown("**ตำรับที่คล้ายกัน** (Jaccard บนชุดสมุนไพร)")
    sim = similar(k, rid, top=5)
    if sim.empty:
        st.info("ข้อมูลไม่พอสำหรับเทียบความคล้าย")
    else:
        sim = sim.assign(name=sim["recipe_id"].map(names), book=sim["recipe_id"].map(dict(zip(rec["recipe_id"], rec["book"]))))
        st.dataframe(sim[["recipe_id", "name", "book", "jaccard", "shared"]], hide_index=True, width="stretch",
                     column_config={"recipe_id": "รหัส", "name": "ชื่อ", "book": "แหล่ง",
                                    "jaccard": st.column_config.NumberColumn("Jaccard", format="%.2f"),
                                    "shared": "สมุนไพรร่วม"})
        st.caption("Jaccard = สมุนไพรร่วม ÷ สมุนไพรทั้งหมดของสองตำรับ (วิธีเริ่มต้น รอทีมยืนยัน)")

    st.markdown("**เทียบ 2 ตำรับ**")
    others = [x for x in ids if x != rid]
    default_b = sim["recipe_id"].iloc[0] if not sim.empty else others[0]
    other = st.selectbox("เทียบกับ", others, index=others.index(default_b) if default_b in others else 0,
                         format_func=lambda x: f"{x} · {names.get(x) or ''}")
    cmp = compare(k, rid, other)
    c = st.columns(3)
    c[0].markdown(f"**มีเฉพาะ {rid}**  \n" + (ui.chips(cmp["only_a"]) or "-"), unsafe_allow_html=True)
    c[1].markdown(f"**มีทั้งคู่** (Jaccard {cmp['jaccard']:.2f})  \n" + (ui.chips(cmp["both"], gold=True) or "-"),
                  unsafe_allow_html=True)
    c[2].markdown(f"**มีเฉพาะ {other}**  \n" + (ui.chips(cmp["only_b"]) or "-"), unsafe_allow_html=True)

# ---------------- 3. modern evidence ----------------
st.markdown("## 3 · หลักฐานวิจัยสมัยใหม่")
with st.container(border=True):
    ev = k.t["evidence"]
    ev = ev[(ev["review_status"] == "verified")
            & (ev["recipe_id"].eq(rid) | ev["herb_id"].isin(herbs["herb_id"]))]
    if ev.empty:
        st.info("ยังไม่มีหลักฐานที่ผ่านการตรวจรับรอง")
    else:
        groups = {"supporting": "สนับสนุน", "not_supporting": "ไม่สนับสนุน", "unclear": "ไม่ชัดเจน"}
        for key, lab in groups.items():
            part = ev[ev["direction"] == key]
            st.markdown(f"**{lab}** ({len(part)})")
            for e in part.to_dict("records"):
                ref = e["pmid"] and f"PMID {e['pmid']}" or e["doi"] or ""
                st.markdown(f"- {e['herb_id'] or 'ทั้งตำรับ'}: {e['finding']} · {e['study_type']} · {ref}")
        st.caption("จำนวนบทความไม่ใช่คะแนนคุณภาพ · ผลของสมุนไพรเดี่ยว/สารเดี่ยวไม่ใช่หลักฐานประสิทธิผลของตำรับ")
ui.footer()
