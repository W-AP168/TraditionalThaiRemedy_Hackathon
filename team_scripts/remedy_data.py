"""โหลดข้อมูลตำรับยา: 3 คัมภีร์ × 2 ไฟล์ = 6 ไฟล์ CSV

แต่ละคัมภีร์มี 2 ไฟล์
  <คัมภีร์>_herbs.csv     1 แถว = 1 ตำรับ × 1 สมุนไพร   (รหัสตำรับ, ชื่อสมุนไพร, ชื่อวิทยาศาสตร์)
  <คัมภีร์>_symptoms.csv  1 แถว = 1 ตำรับ × 1 อาการ     (รหัสตำรับ, อาการ)

ทั้งสองสคริปต์ (Application_search_remedy.py และ Database.py) ใช้ไฟล์นี้ร่วมกัน
จะได้ทำความสะอาดข้อมูลที่เดียว ไม่ต้องเขียนซ้ำ
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# ---- ตั้งค่า: เพิ่ม/ลดคัมภีร์ได้ที่นี่ (เช่น ใส่ "WP" กลับเข้าไป) ----
SCRIPTURES = ["WRO", "NR", "RM"]
HERB_FILE = "{book}_herbs.csv"
SYMPTOM_FILE = "{book}_symptoms.csv"
# (ไม่บังคับ) ไฟล์ชื่อพ้อง 2 คอลัมน์: ชื่อพ้อง, ชื่อหลัก  เช่น  ขิงแห้ง, ขิง
SYNONYM_FILE = "herb_synonyms.csv"

# ชื่อคอลัมน์ที่แต่ละไฟล์อาจพิมพ์ต่างกัน → ชื่อมาตรฐาน
COLUMN_ALIASES = {
    "รหัสตำรับยา": "รหัสตำรับ",
    "ชื่อสมุนไพรตามคัมภีร์": "ชื่อสมุนไพร",
    "ชื่อข้อมูลยา": "ชื่อสมุนไพร",
    "ชื่อทยาศาสตร์": "ชื่อวิทยาศาสตร์",
    "อาการต่างๆ": "อาการ",
    "สรรพคุณ": "อาการ",
}

# 1 เซลล์อาการอาจมีหลายอาการ คั่นด้วย , ; / หรือขึ้นบรรทัดใหม่ → แยกเป็นหลายแถว
# (ไม่แยกด้วยช่องว่าง เพราะอาการภาษาไทยบางอาการมีช่องว่างในชื่อ)
SYMPTOM_SEPARATORS = r"[,;/\n、]+"

MISSING = {"", "-", "nan", "none", "ไม่ระบุ"}


def clean_text(value: object) -> str:
    """ตัดช่องว่างหัวท้าย และรวมช่องว่างซ้ำให้เหลือช่องเดียว"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = " ".join(str(value).split())
    return "" if text.lower() in MISSING else text


def _read(path: Path, required: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = df.columns.str.strip()
    df = df.rename(columns=COLUMN_ALIASES)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} ไม่มีคอลัมน์ {missing} (มีแค่ {list(df.columns)})")
    for col in df.columns:
        df[col] = df[col].map(clean_text)
    # เซลล์ที่ผสาน (merged cells) จาก Excel จะกลายเป็นช่องว่างในแถวล่าง → เติมรหัสตำรับจากแถวบน
    df["รหัสตำรับ"] = df["รหัสตำรับ"].replace("", pd.NA).ffill().fillna("")
    return df


def load_data(data_dir: str | Path = ".", scriptures: list[str] = SCRIPTURES,
              synonyms: dict[str, str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """คืนค่า (herbs, symptoms) ที่สะอาดแล้ว

    herbs:    คัมภีร์, รหัสตำรับ, ชื่อสมุนไพร, ชื่อวิทยาศาสตร์   (1 ตำรับ × 1 สมุนไพร ไม่ซ้ำ)
    symptoms: คัมภีร์, รหัสตำรับ, อาการ                           (1 ตำรับ × 1 อาการ ไม่ซ้ำ)
    synonyms: {"ขิงแห้ง": "ขิง", ...} รวมชื่อพ้องเป็นชื่อเดียว
              (ถ้าไม่ส่งมา จะอ่านจาก herb_synonyms.csv ในโฟลเดอร์เดียวกัน ถ้ามี)
    """
    data_dir = Path(data_dir)
    herb_parts, symptom_parts = [], []
    for book in scriptures:
        h = _read(data_dir / HERB_FILE.format(book=book), ["รหัสตำรับ", "ชื่อสมุนไพร"])
        if "ชื่อวิทยาศาสตร์" not in h.columns:
            h["ชื่อวิทยาศาสตร์"] = ""
        herb_parts.append(h[["รหัสตำรับ", "ชื่อสมุนไพร", "ชื่อวิทยาศาสตร์"]].assign(คัมภีร์=book))

        s = _read(data_dir / SYMPTOM_FILE.format(book=book), ["รหัสตำรับ", "อาการ"])
        s["อาการ"] = s["อาการ"].str.split(SYMPTOM_SEPARATORS, regex=True)
        s = s.explode("อาการ")
        s["อาการ"] = s["อาการ"].map(clean_text)
        symptom_parts.append(s[["รหัสตำรับ", "อาการ"]].assign(คัมภีร์=book))

    herbs = pd.concat(herb_parts, ignore_index=True)
    symptoms = pd.concat(symptom_parts, ignore_index=True)

    if synonyms is None and (data_dir / SYNONYM_FILE).exists():
        syn = pd.read_csv(data_dir / SYNONYM_FILE, encoding="utf-8-sig", dtype=str)
        synonyms = {clean_text(a): clean_text(b) for a, b in syn.iloc[:, :2].itertuples(index=False)}
        print(f"ใช้ไฟล์ชื่อพ้อง {SYNONYM_FILE}: {len(synonyms)} ชื่อ")
    if synonyms:
        herbs["ชื่อสมุนไพร"] = herbs["ชื่อสมุนไพร"].replace(synonyms)

    # ตัดแถวว่าง และแถวซ้ำ (สมุนไพรเดียวกันในตำรับเดียวกันนับครั้งเดียว)
    herbs = herbs[(herbs["รหัสตำรับ"] != "") & (herbs["ชื่อสมุนไพร"] != "")]
    herbs = herbs.drop_duplicates(["รหัสตำรับ", "ชื่อสมุนไพร"]).reset_index(drop=True)
    symptoms = symptoms[(symptoms["รหัสตำรับ"] != "") & (symptoms["อาการ"] != "")]
    symptoms = symptoms.drop_duplicates(["รหัสตำรับ", "อาการ"]).reset_index(drop=True)
    return herbs[["คัมภีร์", "รหัสตำรับ", "ชื่อสมุนไพร", "ชื่อวิทยาศาสตร์"]], symptoms[["คัมภีร์", "รหัสตำรับ", "อาการ"]]


def check_data(herbs: pd.DataFrame, symptoms: pd.DataFrame) -> list[str]:
    """รายงานปัญหาข้อมูลที่ควรแก้ก่อนวิเคราะห์"""
    notes = []
    h_ids, s_ids = set(herbs["รหัสตำรับ"]), set(symptoms["รหัสตำรับ"])
    if h_ids - s_ids:
        notes.append(f"ตำรับที่มีสมุนไพรแต่ไม่มีอาการ {len(h_ids - s_ids)} ตำรับ เช่น {sorted(h_ids - s_ids)[:5]}")
    if s_ids - h_ids:
        notes.append(f"ตำรับที่มีอาการแต่ไม่มีสมุนไพร {len(s_ids - h_ids)} ตำรับ เช่น {sorted(s_ids - h_ids)[:5]}")
    sci = herbs[herbs["ชื่อวิทยาศาสตร์"] != ""].groupby("ชื่อสมุนไพร")["ชื่อวิทยาศาสตร์"].nunique()
    if (sci > 1).any():
        notes.append(f"สมุนไพรที่มีชื่อวิทยาศาสตร์มากกว่า 1 ชื่อ: {sci[sci > 1].index.tolist()[:10]}")
    # ชื่อคล้ายกันมาก (ต่างกันแค่คำนำหน้า เช่น ราก/ผล/ใบ) อาจเป็นชื่อพ้องที่ยังไม่รวม
    base = herbs["ชื่อสมุนไพร"].str.replace(r"^(ราก|ผล|ใบ|ดอก|เปลือก|เมล็ด|แก่น|หัว|ลูก)", "", regex=True)
    groups = herbs.assign(base=base).groupby("base")["ชื่อสมุนไพร"].unique()
    similar = [list(v) for v in groups if len(v) > 1]
    if similar:
        notes.append(f"ชื่อที่อาจเป็นชนิดเดียวกัน (ตรวจด้วยตา): {similar[:8]}")
    return notes

