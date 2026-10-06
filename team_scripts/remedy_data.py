"""โหลดข้อมูลตำรับยาของทีม (WRO, NR, RM) จากโฟลเดอร์ CSV/Excel

ตั้งชื่อไฟล์อย่างไรก็ได้ ระบบดูจากคอลัมน์ (ตัวอ่านเดียวกับเว็บไซต์: core/ingest.py)
ชื่อพ้องและคณาเภสัชใช้เฉพาะรายการที่ผู้ตรวจยืนยันแล้ว (data/ ของโปรเจกต์)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.data import BOOKS, KB, resolve_items  # noqa: E402
from core.ingest import build_tables, current_reference, read_sources  # noqa: E402

SCRIPTURES = list(BOOKS)
_LAST: dict = {}


def load_data(data_dir: str | Path = ".") -> tuple[pd.DataFrame, pd.DataFrame]:
    """คืนค่า (herbs, symptoms) ชื่อคอลัมน์ภาษาไทย

    herbs:    คัมภีร์, รหัสตำรับ, ชื่อสมุนไพร, ชื่อวิทยาศาสตร์   (หลังแตกคณาเภสัช + รวมชื่อพ้องที่ยืนยันแล้ว)
    symptoms: คัมภีร์, รหัสตำรับ, อาการ
    """
    folder = Path(data_dir)
    files = [(p.name, p) for p in sorted(folder.iterdir()) if p.suffix.lower() in (".csv", ".xlsx", ".xls")]
    imp = read_sources(files)
    t, checks = build_tables(imp, current_reference())
    _LAST["checks"] = checks
    for s in imp.sources:
        if s.kinds == ["skipped"]:
            print(f"⚠️ ข้ามไฟล์ {s.name}: {s.note}")
    if t["recipes"].empty:
        raise FileNotFoundError(f"ไม่พบข้อมูลตำรับใน {folder.resolve()}")
    items = resolve_items(t)
    book = t["recipes"].set_index("recipe_id")["book"]
    sci = dict(zip(t["herbs"]["herb_id"], t["herbs"]["sci_name"]))
    sci_raw = imp.tables["_sci"].drop_duplicates("herb_name_original").set_index("herb_name_original")["sci_name"]
    herbs = pd.DataFrame({
        "คัมภีร์": items["recipe_id"].map(book),
        "รหัสตำรับ": items["recipe_id"],
        "ชื่อสมุนไพร": items["item"],
        "ชื่อวิทยาศาสตร์": [sci.get(h) or sci_raw.get(o, "") for h, o in zip(items["item"], items["herb_name_original"])],
    })
    s = t["recipe_symptoms"]
    symptoms = pd.DataFrame({"คัมภีร์": s["recipe_id"].map(book), "รหัสตำรับ": s["recipe_id"],
                             "อาการ": s["symptom_original"]})
    return herbs.reset_index(drop=True), symptoms.reset_index(drop=True)


def check_data(herbs: pd.DataFrame, symptoms: pd.DataFrame) -> list[str]:
    return [c.detail for c in _LAST.get("checks", []) if not c.ok]
