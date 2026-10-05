"""Every page renders without an exception (uses data/ as committed)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")

PAGES = [
    "pages/home.py",
    "pages/explore.py",
    "pages/symptoms.py",
    "pages/herbs.py",
    "pages/about.py",
    "pages/recipe.py",
    "pages/research.py",
    "pages/apriori_lab.py",
    "pages/statistics.py",
    "pages/graph.py",
    "pages/admin.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.message for e in at.exception]


def test_symptom_search_shows_results():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.switch_page("pages/symptoms.py")
    at.session_state["main_symptom"] = "ไข้"
    at.run()
    assert not at.exception
    assert any("ตำรับที่มีข้อมูลสอดคล้อง" in m.value for m in at.markdown)
