import time

import streamlit as st

import ui
from core.data import BOOKS
from core.gate import INDUSTRY, research_mode
from core.recommend import recommend
from core.scoring import split_terms, unknown_terms

k = ui.header("คัดเลือกตำรับ", "Recommend · ตรวจความพร้อมของสมุนไพรทุกตัวก่อนจัดอันดับ")
s = ui.conf()

with st.container(border=True):
    c1, c2 = st.columns(2)
    syms = c1.multiselect("อาการ", k.symptom_terms(), key="rec_sym", placeholder="เช่น ไอ, มีเสมหะ")
    inds = c2.multiselect("ข้อบ่งใช้ (โรค)", k.indication_terms(), key="rec_ind",
                          placeholder="ยังไม่มีข้อมูลข้อบ่งใช้" if not k.indication_terms() else "เลือกข้อบ่งใช้")
    free = st.text_input("หรือพิมพ์คำเพิ่ม (คั่นด้วย ,)", key="rec_free", placeholder="ต้องตรงกับคำในฐานข้อมูลทั้งคำ")
    c3, c4 = st.columns(2)
    mode_key = c3.radio("โหมด", ["industry", "research"], horizontal=True, key="rec_mode",
                        format_func={"industry": "Industry (ค่าเริ่มต้น)", "research": "Research"}.get)
    books = c4.multiselect("แหล่ง", list(BOOKS), default=list(BOOKS), format_func=ui.book_label, key="rec_books")

mode = INDUSTRY if mode_key == "industry" else research_mode(s)
st.caption(f"เกณฑ์ที่ใช้: Identity ∈ {{{', '.join(mode.identity_allowed)}}} และ "
           f"Availability ∈ {{{', '.join(mode.availability_allowed)}}} ทุกตัวในตำรับ · ไม่เฉลี่ย"
           + ("" if mode.industry else f" · ตั้งโดย {s.get('research_set_by') or 'ยังไม่ระบุ'} · "
              "โหมดวิจัยไม่ใช่ระดับอุตสาหกรรม และไม่แทนสมุนไพรให้อัตโนมัติ"))
ui.grade_legend()

extra = split_terms(free)
vocab_s, vocab_i = set(k.symptom_terms()), set(k.indication_terms())
q_sym = list(syms) + [t for t in extra if t in vocab_s]
q_ind = list(inds) + [t for t in extra if t in vocab_i and t not in vocab_s]
missing = unknown_terms(k, extra, [])
if missing:
    st.warning(f"ไม่พบคำเหล่านี้ในฐานข้อมูล (ต้องตรงทั้งคำ): {', '.join(missing)}")
if not q_sym and not q_ind:
    st.info("เลือกอาการหรือข้อบ่งใช้อย่างน้อย 1 คำ")
    ui.footer()
    st.stop()

t0 = time.perf_counter()
ready, limited = recommend(k, q_sym, q_ind, books, mode, s["weight_symptom"], s["weight_indication"])
ms = (time.perf_counter() - t0) * 1000
st.caption(f"ความเกี่ยวข้อง = (อาการที่ตรง/อาการที่ค้น × {s['weight_symptom']} + ข้อบ่งใช้ที่ตรง/ที่ค้น × "
           f"{s['weight_indication']}) ÷ น้ำหนักรวม · **ไม่ใช่โอกาสที่การรักษาจะได้ผล** · ค้นใน {ms:.0f} ms")


def card(r, key: str) -> None:
    rec = k.recipe(r.gate.recipe_id)
    with st.container(border=True):
        top = st.columns([3, 1])
        top[0].markdown(f"**{ui.esc(rec['name'] or r.gate.recipe_id)}**  \n"
                        f"<span class='mono'>{ui.esc(r.gate.recipe_id)}</span> · {ui.esc(ui.book_label(rec['book']))}",
                        unsafe_allow_html=True)
        top[1].metric("ความเกี่ยวข้อง", f"{r.match.score:.2f}", help=r.match.breakdown)
        ui.md(f"{ui.esc(r.match.breakdown)} &nbsp; Identity {ui.status_badge(r.gate.identity_status)} "
              f"Availability {ui.status_badge(r.gate.availability_status)}")
        lines = []
        for h in r.gate.herbs:
            grp = f" <small>(จาก{ui.esc(h.from_group)})</small>" if h.from_group else ""
            name = ui.esc(k.herb_name(h.herb_id) or h.herb_name_original)
            style = "color:#8A2E0E;font-weight:700" if h.problems else ""
            prob = f" <small style='color:#8A2E0E'>← {ui.esc('; '.join(h.problems))}</small>" if h.problems else ""
            lines.append(f"<span style='{style}'>{name}</span>{grp} {ui.herb_badges(k, h.herb_id)}{prob}")
        ui.md("<br>".join(lines))
        for h in r.gate.herbs:
            if h.herb_id:
                ui.md(ui.safety_html(k, h.herb_id))
        b1, b2 = st.columns(2)
        with b1.popover("ข้อความต้นฉบับ"):
            st.write(rec["original_text"] or "ยังไม่มีข้อความต้นฉบับ")
            st.caption(f"สรรพคุณตามตำรา: {rec['indication_text'] or '-'}")
        if b2.button("วิเคราะห์ตำรับนี้ →", key=f"an-{key}-{r.gate.recipe_id}", width="stretch"):
            ui.open_analyze(r.gate.recipe_id)


st.markdown(f"### ✅ ผ่านเกณฑ์เพื่อพัฒนา ({len(ready)})")
st.caption(mode.label)
if not ready:
    st.info("ยังไม่มีตำรับที่สมุนไพรทุกตัวผ่านเกณฑ์ ดูสาเหตุได้ในกลุ่มด้านล่าง")
for r in ready:
    card(r, "r")

st.markdown(f"### ⚠️ ตรงโจทย์แต่ยังมีข้อจำกัด ({len(limited)})")
st.caption("แสดงสมุนไพรที่เป็นข้อจำกัด และแกนที่ไม่ผ่าน/ไม่มีข้อมูล · ความเกี่ยวข้องสูงไม่ชดเชยสมุนไพรที่ไม่ผ่าน")
show = st.session_state.get("rec_show", 10)
for r in limited[:show]:
    card(r, "l")
if len(limited) > show and st.button(f"แสดงเพิ่ม ({len(limited) - show})"):
    st.session_state["rec_show"] = show + 10
    st.rerun()
ui.footer()
