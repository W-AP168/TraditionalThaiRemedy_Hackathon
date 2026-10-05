"""โหลดข้อมูลตำรับยาของทีม (คัมภีร์ WRO, NR, WP) จากโฟลเดอร์ CSV

ตั้งชื่อไฟล์อย่างไรก็ได้ ระบบดูจากคอลัมน์:
  มี รหัสตำรับ + ชื่อสมุนไพร       → ไฟล์สมุนไพร  (1 แถว = 1 ตำรับ × 1 สมุนไพร)
  มี รหัสตำรับ + อาการ/สรรพคุณ     → ไฟล์อาการ    (1 แถว = 1 ตำรับ × 1 อาการ)
  มีทั้งสองอย่าง (ไฟล์แบบเก่า)       → อ่านได้ทั้งสองแบบ
คัมภีร์ดูจากรหัสตำรับ (WRO133/1 → WRO) แถวของคัมภีร์อื่น (เช่น RM) จะถูกข้าม

ตัวอ่านไฟล์จริงอยู่ที่ core/team_csv.py ใช้ร่วมกับเว็บไซต์ (แก้ที่เดียว ใช้ได้ทั้งคู่)
เพิ่ม/ลดคัมภีร์ได้ที่ SCRIPTURE_NAMES ใน core/team_csv.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.team_csv import SCRIPTURES, quality_notes, read_folder  # noqa: E402

__all__ = ["SCRIPTURES", "load_data", "check_data"]
_LAST = {}


def load_data(data_dir: str | Path = ".") -> tuple[pd.DataFrame, pd.DataFrame]:
    """คืนค่า (herbs, symptoms) ที่สะอาดแล้ว ชื่อคอลัมน์ภาษาไทย

    herbs:    คัมภีร์, รหัสตำรับ, ชื่อสมุนไพร, ชื่อวิทยาศาสตร์   (1 ตำรับ × 1 สมุนไพร ไม่ซ้ำ)
    symptoms: คัมภีร์, รหัสตำรับ, อาการ                           (1 ตำรับ × 1 อาการ ไม่ซ้ำ)
    """
    td = read_folder(data_dir)
    _LAST["td"] = td
    for f in td.files:
        if f.kind == "skipped":
            print(f"⚠️ ข้ามไฟล์ {f.name}: {f.note}")
    if td.herbs.empty and td.symptoms.empty:
        raise FileNotFoundError(f"ไม่พบไฟล์ CSV ที่มีรหัสตำรับ + สมุนไพร/อาการ ใน {Path(data_dir).resolve()}")
    herbs = td.herbs.rename(columns={"book": "คัมภีร์", "recipe_id": "รหัสตำรับ", "herb": "ชื่อสมุนไพร",
                                     "sci_name": "ชื่อวิทยาศาสตร์"})
    symptoms = td.symptoms.rename(columns={"book": "คัมภีร์", "recipe_id": "รหัสตำรับ", "symptom": "อาการ"})
    return (herbs[["คัมภีร์", "รหัสตำรับ", "ชื่อสมุนไพร", "ชื่อวิทยาศาสตร์"]].reset_index(drop=True),
            symptoms[["คัมภีร์", "รหัสตำรับ", "อาการ"]].reset_index(drop=True))


def check_data(herbs: pd.DataFrame, symptoms: pd.DataFrame) -> list[str]:
    """รายงานปัญหาข้อมูลของการโหลดครั้งล่าสุด"""
    return quality_notes(_LAST["td"]) if "td" in _LAST else []
