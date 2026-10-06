"""Shared Streamlit pieces: theme, cached data, badges, disclaimers, password gate."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from core import rules as R
from core.data import AVAILABILITY_GRADES, BOOKS, DATA_DIR, IDENTITY_GRADES, KB, load, settings

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Thai:wght@600;700&family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');
html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea { font-family: 'IBM Plex Sans Thai', system-ui, sans-serif; }
h1, h2, h3 { font-family: 'Noto Serif Thai', serif !important; color: #16302A; }
.mono { font-family: 'IBM Plex Mono', monospace; }
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.8rem; font-weight:600; margin-right:4px; white-space:nowrap; }
.b-mock { background:#F3EAD3; color:#5C4612; border:1px dashed #B08D3C; }
.b-real { background:#E4EDE6; color:#16302A; }
.b-ok { background:#E4EDE6; color:#16302A; }
.b-fail { background:#FDF0E6; color:#8A2E0E; }
.b-na { background:#ECE6D6; color:#3E4A43; }
.b-pending { background:#ECE6D6; color:#3E4A43; border:1px dashed #8A8F87; }
.g { display:inline-block; min-width:22px; text-align:center; padding:1px 6px; border-radius:6px; font-family:'IBM Plex Mono',monospace; font-size:.8rem; margin-right:2px; cursor:help; }
.g-A { background:#16302A; color:#fff; } .g-B { background:#1F4D3A; color:#fff; } .g-C { background:#B08D3C; color:#fff; }
.g-D { background:#8A2E0E; color:#fff; } .g-E { background:#4A1A08; color:#fff; } .g-x { background:#ECE6D6; color:#3E4A43; }
.warn { background:#FDF0E6; border:1px solid #F0C9A8; border-left:4px solid #B42318; border-radius:10px; padding:8px 12px; color:#4A1A08; margin:4px 0; }
.chip { display:inline-block; padding:2px 10px; margin:2px 4px 2px 0; border-radius:999px; background:#E4EDE6; color:#16302A; font-size:.9rem; }
.chip.gold { background:#F3EAD3; color:#5C4612; }
.note { background:#ECE6D6; border-radius:10px; padding:10px 14px; color:#3E4A43; font-size:.92rem; }
.hypo { background:#F3EAD3; border:2px solid #B08D3C; border-radius:12px; padding:10px 14px; color:#3A2E10; font-weight:700; }
.footer { margin-top:40px; padding-top:12px; border-top:1px solid #E3DCCB; color:#55605A; font-size:.85rem; }
</style>
"""

FOOTER = ("ThaiRx-AI เป็นเครื่องมือเพื่อการวิจัยและการศึกษาสำหรับแพทย์แผนไทย นักวิจัย และนักศึกษา "
          "ไม่ใช่เครื่องมือสั่งจ่ายยา และไม่ใช่คำแนะนำการรักษาสำหรับประชาชน")


def setup() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(s: object) -> str:
    return html.escape(str(s))


def md(htm: str) -> None:
    st.markdown(htm, unsafe_allow_html=True)


# ---------- data ----------

def _log_key() -> int:
    p = DATA_DIR / "review_log.csv"
    return p.stat().st_mtime_ns if p.exists() else 0


@st.cache_resource(show_spinner=False)
def _kb(fp_and_log: tuple) -> KB:
    return load()


def kb() -> KB:
    from core.data import fingerprint
    return _kb((fingerprint(), _log_key()))


def refresh() -> None:
    st.cache_resource.clear()
    st.cache_data.clear()


@st.cache_data(show_spinner="กำลังคำนวณกฎ Apriori…")
def rules(fp: str, version: str, params: R.Params) -> tuple[pd.DataFrame, dict]:
    return R.cached_rules(kb(), params)


def get_rules(params: R.Params) -> tuple[pd.DataFrame, dict]:
    """Rules for these params; the "ข้อมูลน้อย" threshold comes from the back-end settings."""
    from dataclasses import replace
    k = kb()
    return rules(k.fingerprint, k.version, replace(params, low_count=int(conf()["low_support_count"])))


def conf() -> dict:
    return settings()


# ---------- badges ----------

def data_badge(k: KB | None = None) -> str:
    k = k or kb()
    if k.is_sample:
        return '<span class="badge b-mock" title="ข้อมูลจำลองเพื่อทดสอบระบบ ไม่ใช่ข้อมูลจากคัมภีร์จริง">จำลอง</span>'
    return '<span class="badge b-real" title="คำนวณจากข้อมูลจริงที่นำเข้า">คำนวณจริง</span>'


MOCK = '<span class="badge b-mock" title="หน้าจอ/ค่าจำลอง ยังไม่ได้เชื่อมข้อมูลจริง">จำลอง</span>'


def header(title: str, subtitle: str = "") -> KB:
    k = kb()
    st.title(title)
    md(f'{data_badge(k)} <span class="badge b-na">ข้อมูล v{esc(k.version)}</span>'
       + (f'<span style="color:#55605A"> · {esc(subtitle)}</span>' if subtitle else ""))
    if k.is_sample:
        st.caption("ตอนนี้ใช้ข้อมูลจำลอง (สังเคราะห์) ทุกตัวเลขยังไม่ใช่ผลจากคัมภีร์จริง")
    for w in k.warnings:
        if w.startswith("ไม่พบไฟล์หลัก"):
            st.error(f"{w} → ข้อมูลไม่พอ นำเข้าข้อมูลที่หน้า Back-end")
    return k


def grade_chip(axis: str, value: str) -> str:
    names = IDENTITY_GRADES if axis == "ID" else AVAILABILITY_GRADES
    full = "Identity Certainty" if axis == "ID" else "Raw Material Availability"
    if not value:
        return f'<span class="g g-x" title="{full}: ยังไม่มีเกรด">{axis} ?</span>'
    return (f'<span class="g g-{esc(value)}" title="{full} {esc(value)}: {esc(names.get(value, ""))}">'
            f"{axis} {esc(value)}</span>")


def herb_badges(k: KB, herb_id: str) -> str:
    if not herb_id:
        return '<span class="badge b-pending">รอตรวจสอบ</span>'
    g = k.grade(herb_id)
    return grade_chip("ID", g.get("identity", "")) + grade_chip("AV", g.get("availability", ""))


def safety_html(k: KB, herb_id: str) -> str:
    return "".join(f'<div class="warn">⚠️ <b>{esc(k.herb_name(herb_id))}</b>: {esc(s["warning_text"])}'
                   f'<br><small>แหล่ง: {esc(s["source"] or "ไม่ระบุ")}</small></div>' for s in k.safety(herb_id))


def status_badge(status: str) -> str:
    cls = {"ผ่าน": "b-ok", "ไม่ผ่าน": "b-fail", "ข้อมูลไม่พอ": "b-na"}.get(status, "b-na")
    return f'<span class="badge {cls}">{esc(status)}</span>'


def chips(items, gold: bool = False) -> str:
    cls = "chip gold" if gold else "chip"
    return "".join(f'<span class="{cls}">{esc(i)}</span>' for i in items)


def grade_legend() -> None:
    with st.expander("ความหมายของเกรด"):
        a, b = st.columns(2)
        a.markdown("**Identity Certainty (ID)**\n\n" + "\n".join(f"- **{g}** {d}" for g, d in IDENTITY_GRADES.items()))
        b.markdown("**Raw Material Availability (AV)**\n\n"
                   + "\n".join(f"- **{g}** {d}" for g, d in AVAILABILITY_GRADES.items()))
        st.caption("สองแกนเป็นอิสระต่อกัน · เกรด A ไม่ได้แปลว่าปลอดภัยหรือผ่านคุณภาพทุกล็อต · "
                   "คำเตือนความปลอดภัยแยกจากเกรด")


def rules_meta(meta: dict) -> str:
    return (f"{meta.get('analysis_label', '')} · ธุรกรรม (ตำรับ) {meta.get('n_transactions', 0):,} · "
            f"support ≥ {meta.get('min_support')} · confidence ≥ {meta.get('min_confidence')} · "
            f"lift ≥ {meta.get('min_lift')} · คัมภีร์ {', '.join(meta.get('books', []))} · "
            f"{'รวม' if meta.get('include_duplicates') else 'ไม่รวม'}ตำรับซ้ำ · ข้อมูล v{meta.get('data_version')} · "
            f"ใช้เวลา {meta.get('runtime_sec', 0)} วินาที")


def rules_disclaimer() -> None:
    md(f'<div class="note">{esc(R.DISCLAIMER)}</div>')


def footer() -> None:
    md(f'<div class="footer">{esc(FOOTER)}</div>')


def book_label(code: str) -> str:
    return f"{code} · {BOOKS.get(code, '')}"


def open_analyze(recipe_id: str) -> None:
    st.session_state["analyze_id"] = recipe_id
    st.switch_page("pages/2_Analyze.py")


# ---------- back-end password ----------

def backend_gate() -> bool:
    try:
        pw = st.secrets.get("lab_password")
    except Exception:
        pw = None
    if st.session_state.get("backend_ok"):
        return True
    if not pw:
        st.warning("ยังไม่ได้ตั้งรหัสผ่าน Back-end (lab_password ใน .streamlit/secrets.toml) "
                   "เปิดให้ใช้ได้ชั่วคราวสำหรับการพัฒนา ตั้งรหัสก่อนเผยแพร่", icon="🔓")
        return True
    st.subheader("🔒 Back-end สำหรับนักวิจัย / กรรมการ")
    entered = st.text_input("รหัสผ่าน", type="password")
    if entered:
        if entered == pw:
            st.session_state["backend_ok"] = True
            st.rerun()
        st.error("รหัสผ่านไม่ถูกต้อง")
    return False
