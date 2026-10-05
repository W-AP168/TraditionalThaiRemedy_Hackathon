"""Shared Streamlit helpers: theme, cached data access, small UI pieces."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from core import cache
from core.apriori import apriori, association_rules, binary_matrix, filter_rules, herb_pairs
from core.data_loader import Dataset, fingerprint, load_dataset
from core.safety import DISCLAIMER, LEVEL_LABEL
from core.statistics import permutation_test, run_pair_tests

N_PERM = 1000

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Thai:wght@600;700&family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');
html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea { font-family: 'IBM Plex Sans Thai', system-ui, sans-serif; }
h1, h2, h3, .serif { font-family: 'Noto Serif Thai', serif !important; color: #16302A; }
.mono { font-family: 'IBM Plex Mono', monospace; }
.hero { background: #16302A; color: #F7F3EA; border-radius: 20px; padding: 56px 44px; margin-bottom: 8px; }
.hero h1 { color: #F7F3EA !important; font-size: 3rem; line-height: 1.3; margin: 0 0 16px; }
.hero p { color: #CFE0D3; font-size: 1.15rem; max-width: 560px; }
.hero .eyebrow { color: #E2C27A; font-size: .8rem; letter-spacing: .1em; font-weight: 600; }
.hero .stats { display: flex; gap: 48px; flex-wrap: wrap; margin-top: 28px; padding-top: 24px; border-top: 1px solid #2F5444; }
.hero .stats b { display: block; font-family: 'Noto Serif Thai', serif; font-size: 2.3rem; color: #F7F3EA; }
.hero .stats span { color: #CFE0D3; }
.chip { display: inline-block; padding: 3px 12px; margin: 2px 4px 2px 0; border-radius: 999px; background: #E4EDE6; color: #16302A; font-size: .9rem; }
.chip.gold { background: #F3EAD3; color: #5C4612; }
.badge-caution, .badge-danger { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .85rem; font-weight: 600; }
.badge-caution { background: #FDF0E6; color: #8A2E0E; }
.badge-danger { background: #8A2E0E; color: #FFFFFF; }
.warnbox { background: #FDF0E6; border: 1px solid #F0C9A8; border-radius: 14px; padding: 18px 20px; color: #4A1A08; }
.warnbox b { color: #8A2E0E; }
.note { background: #ECE6D6; border-radius: 12px; padding: 12px 16px; color: #3E4A43; font-size: .95rem; }
.interp { background: #F3EAD3; border-radius: 12px; padding: 14px 16px; color: #3A2E10; }
.scorebar { height: 8px; border-radius: 4px; background: #ECE6D6; }
.scorebar > div { height: 100%; border-radius: 4px; background: #1F4D3A; }
.assoc { display: flex; flex-direction: column; align-items: center; gap: 0; }
.assoc .herb { padding: 8px 20px; border-radius: 999px; background: #E4EDE6; font-size: 1.2rem; font-weight: 600; color: #16302A; }
.assoc .stem { width: 3px; height: 22px; background: #1F4D3A; }
.assoc .val { padding: 4px 12px; border-radius: 8px; background: #16302A; color: #E2C27A; font-family: 'IBM Plex Mono', monospace; }
</style>
"""


def setup() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(s: object) -> str:
    return html.escape(str(s))


# ---------- data (cached) ----------

@st.cache_resource(show_spinner=False)
def _load(fp: str) -> Dataset:
    return load_dataset()


def ds() -> Dataset:
    return _load(fingerprint())


@st.cache_resource(show_spinner=False)
def _matrix(fp: str, include_symptoms: bool) -> pd.DataFrame:
    return binary_matrix(_load(fp), include_symptoms=include_symptoms)


def matrix(include_symptoms: bool = False) -> pd.DataFrame:
    return _matrix(ds().fingerprint, include_symptoms)


@st.cache_data(show_spinner="กำลังวิเคราะห์ Apriori…")
def rules(fp: str, kind: str, min_support: float, min_confidence: float, min_lift: float) -> pd.DataFrame:
    params = {"kind": kind, "s": min_support, "c": min_confidence, "l": min_lift}

    def compute() -> pd.DataFrame:
        m = _matrix(fp, kind != "herb")
        its = apriori(m, min_support, max_len=3)
        r = association_rules(its, len(m), min_confidence, min_lift)
        return filter_rules(r, kind)

    return cache.cached("rules", fp, params, compute)


@st.cache_data(show_spinner=False)
def pairs(fp: str, min_count: int = 3) -> pd.DataFrame:
    return cache.cached("pairs", fp, {"min_count": min_count}, lambda: herb_pairs(_matrix(fp, False), min_count))


@st.cache_data(show_spinner="กำลังทดสอบด้วย permutation test…")
def pair_tests(fp: str, top: int = 30) -> pd.DataFrame:
    def compute() -> pd.DataFrame:
        p = herb_pairs(_matrix(fp, False), 3).head(top)
        return run_pair_tests(_matrix(fp, False), p, n_perm=N_PERM)

    return cache.cached("pair_tests", fp, {"top": top, "n": N_PERM}, compute)


@st.cache_data(show_spinner=False)
def one_test(fp: str, a: str, b: str) -> dict:
    return cache.cached("perm", fp, {"a": a, "b": b, "n": N_PERM},
                        lambda: permutation_test(_matrix(fp, False), a, b, n_perm=N_PERM))


# ---------- small UI pieces ----------

def chips(items, gold: bool = False) -> str:
    cls = "chip gold" if gold else "chip"
    return "".join(f'<span class="{cls}">{esc(i)}</span>' for i in items)


def safety_badge(level: str) -> str:
    if level in ("caution", "danger"):
        return f'<span class="badge-{level}">{LEVEL_LABEL[level]}</span>'
    return ""


def disclaimer() -> None:
    st.markdown(f'<div class="note">{esc(DISCLAIMER)}</div>', unsafe_allow_html=True)


def dataset_caption() -> str:
    d = ds()
    v = d.meta.get("version", "?")
    sample = " · ข้อมูลตัวอย่าง (ยังไม่ใช่ข้อมูลจริง)" if d.meta.get("is_sample") else ""
    return f"Dataset v{v} · {d.meta.get('updated', '')}{sample}"


def sample_banner() -> None:
    if ds().meta.get("is_sample"):
        st.info("ตอนนี้ระบบใช้ **ข้อมูลตัวอย่าง** ที่สร้างขึ้นเพื่อทดสอบ ตัวเลขทั้งหมดยังไม่ใช่ผลจากคัมภีร์จริง "
                "อัปโหลดข้อมูลจริงได้ที่หน้า จัดการข้อมูล", icon="ℹ️")


def open_recipe(recipe_id: str) -> None:
    st.session_state["recipe_id"] = recipe_id
    st.switch_page("pages/recipe.py")


def open_herb(herb_id: str) -> None:
    st.session_state["herb_id"] = herb_id
    st.switch_page("pages/herbs.py")


def lab_gate() -> bool:
    """Optional password for the Research Lab: set lab_password in .streamlit/secrets.toml."""
    try:
        pw = st.secrets.get("lab_password")
    except Exception:
        pw = None
    if not pw or st.session_state.get("lab_ok"):
        return True
    st.markdown("### 🔬 Research Lab")
    entered = st.text_input("รหัสผ่านสำหรับนักวิจัย / กรรมการ", type="password")
    if entered:
        if entered == pw:
            st.session_state["lab_ok"] = True
            st.rerun()
        st.error("รหัสผ่านไม่ถูกต้อง")
    return False
