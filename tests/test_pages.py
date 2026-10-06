"""Every page renders on the committed sample data, and the demo path works."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["pages/0_Home.py", "pages/1_Recommend.py", "pages/2_Analyze.py", "pages/3_Discover.py",
         "pages/9_Backend.py"]


def open_page(page: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    at.switch_page(page)
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = open_page(page)
    assert not at.exception, [e.message for e in at.exception]


def test_demo_path_cough_with_phlegm():
    at = open_page("pages/1_Recommend.py")
    at.multiselect(key="rec_sym").set_value(["ไอ", "มีเสมหะ"]).run()
    assert not at.exception
    heads = [m.value for m in at.markdown if m.value.startswith("###")]
    assert any("ผ่านเกณฑ์เพื่อพัฒนา" in h for h in heads)
    assert any("ตรงโจทย์แต่ยังมีข้อจำกัด" in h for h in heads)


def test_discover_has_fixed_label():
    at = open_page("pages/3_Discover.py")
    at.multiselect(key="dis_sym").set_value(["ปวดข้อ"]).run()
    assert not at.exception
    assert sum("สมมติฐานเพื่อการวิจัย — ต้องประเมินโดยผู้เชี่ยวชาญ" in m.value for m in at.markdown) >= 1
