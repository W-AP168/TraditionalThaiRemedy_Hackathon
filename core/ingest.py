"""Team files (CSV or Excel) → the tables of core/data.py.

Every CSV, or every sheet of an Excel file, is recognised by its COLUMNS, so file
names don't matter (recipes_WRO.csv, herbs_NR.csv, symptoms_NR.csv, the team
workbook …). One file may feed several tables. Book (WRO / NR / RM) comes from
the recipe id prefix, else from the file/sheet name. Other books are skipped
and reported.

Excel is read with engine="calamine" (openpyxl fails on the team workbook).
"""

from __future__ import annotations

import io
import json
import re
import shutil
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from core.data import BOOKS, DATA_DIR, SCHEMA, clean, read_table, save_table

ALIASES: dict[str, list[str]] = {
    "recipe_id": ["รหัสตำรับ", "รหัสตำรับยา", "รหัส", "recipe_id"],
    "book": ["คัมภีร์", "แหล่งที่มา", "book"],
    "name": ["ชื่อตำรับ", "ชื่อตำรับยา", "ชื่อยา", "name", "recipe_name", "name_th"],
    "original_text": ["ข้อความต้นฉบับ", "ข้อความเดิม", "ข้อความจากคัมภีร์", "ข้อความตามตำรา", "ต้นฉบับ",
                      "original_text"],
    "indication_text": ["สรรพคุณ", "indication_text"],
    "preparation": ["วิธีทำ", "วิธีเตรียม", "วิธีปรุง", "preparation"],
    "vehicle": ["กระสายยา", "น้ำกระสาย", "น้ำกระสายยา", "vehicle"],
    "dosage_form": ["รูปแบบยา", "รูปแบบ", "dosage_form", "form"],
    "usage": ["วิธีใช้", "usage"],
    "category": ["หมวด", "หมวดหมู่", "ประเภท", "category"],
    "duplicate_of": ["ซ้ำกับ", "ซ้ำกับตำรับ", "duplicate_of"],
    "herb": ["ชื่อสมุนไพร", "ชื่อสมุนไพรตามคัมภีร์", "ชื่อข้อมูลยา", "สมุนไพร", "herb", "herb_name_original",
             "herb_raw", "herb_name"],
    "sci_name": ["ชื่อวิทยาศาสตร์", "ชื่อทยาศาสตร์", "ชื่อวิทย์", "sci_name", "scientific_name"],
    "part_used": ["ส่วนที่ใช้", "ส่วนใช้", "part_used"],
    "qty_original": ["ปริมาณ", "จำนวน", "qty_original", "amount", "qty"],
    "unit_original": ["หน่วย", "unit_original", "unit"],
    "qty_percent": ["ร้อยละ", "qty_percent", "percent"],
    "symptom": ["อาการ", "อาการต่างๆ", "อาการต่าง ๆ", "symptom", "symptom_original"],
    "symptom_modern": ["อาการสมัยใหม่", "symptom_modern"],
    "mapping_reason": ["เหตุผลการเทียบ", "mapping_reason"],
    "mapped_by": ["ผู้เทียบ", "mapped_by"],
    "indication": ["ข้อบ่งใช้", "โรค", "indication"],
    # reference tables
    "herb_id": ["herb_id", "รหัสสมุนไพร"],
    "std_name_th": ["ชื่อมาตรฐาน", "std_name_th"],
    "alias": ["ชื่อพ้อง", "alias", "synonym"],
    "group_name": ["คณาเภสัช", "ชื่อกลุ่ม", "group_name"],
    "identity": ["identity", "ความชัดเจนของชนิด", "เกรดชนิด"],
    "availability": ["availability", "ความพร้อมของวัตถุดิบ", "เกรดวัตถุดิบ"],
    "warning_text": ["คำเตือน", "ข้อควรระวัง", "warning_text"],
    "source": ["แหล่งอ้างอิง", "source"],
    "reason": ["เหตุผล", "reason"],
    "assessor": ["ผู้ประเมิน", "assessor"],
    "assessed_date": ["วันที่ประเมิน", "assessed_date"],
    "supply_area": ["แหล่งผลิต", "supply_area"],
    "season": ["ฤดู", "season"],
    "volume_note": ["ปริมาณที่หาได้", "volume_note"],
    "reviewed_by": ["ผู้ตรวจ", "reviewed_by"],
    "review_status": ["สถานะ", "review_status"],
    "taste": ["รสยา", "taste"],
    "pikat": ["พิกัดยา", "pikat"],
}
_LOOKUP = {a.strip().lower(): std for std, names in ALIASES.items() for a in names}
RECIPE_FIELDS = ["name", "original_text", "indication_text", "preparation", "vehicle", "dosage_form", "usage",
                 "category", "duplicate_of"]
SPLIT = r"[,;/\n、]+"   # several symptoms/indications in one cell
_PREFIX = re.compile(r"^([A-Za-z]+)")
_QTY = re.compile(r"^\s*([0-9๐-๙]+(?:[./][0-9๐-๙]+)?)\s*(.*)$")
_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def book_of(recipe_id: str) -> str:
    m = _PREFIX.match(recipe_id or "")
    return m.group(1).upper() if m else ""


def _book_from_name(name: str) -> str:
    stem = re.sub(r"\.(csv|xlsx?)$", "", name, flags=re.I).upper()
    for code in sorted(BOOKS, key=len, reverse=True):
        if re.search(rf"(^|[^A-Z]){code}([^A-Z]|$)", stem):
            return code
    return ""


@dataclass
class Source:
    name: str
    kinds: list[str]
    book: str
    rows: int
    note: str = ""


@dataclass
class Imported:
    tables: dict[str, pd.DataFrame]
    sources: list[Source] = field(default_factory=list)
    skipped_books: dict[str, int] = field(default_factory=dict)


def _frames(name: str, raw: bytes) -> list[tuple[str, pd.DataFrame]]:
    if name.lower().endswith((".xlsx", ".xls")):
        try:
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str, engine="calamine")
        except Exception:
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str)
        return [(f"{name}:{s}", df.fillna("")) for s, df in sheets.items()]
    for enc in ("utf-8-sig", "cp874"):
        try:
            return [(name, pd.read_csv(io.BytesIO(raw), dtype=str, encoding=enc, keep_default_na=False))]
        except UnicodeDecodeError:
            continue
    raise ValueError("อ่านไฟล์ไม่ได้ (ไม่ใช่ UTF-8 หรือ Thai cp874)")


def _standardise(df: pd.DataFrame) -> pd.DataFrame:
    keep = {}
    for col in df.columns:
        std = _LOOKUP.get(str(col).strip().lower())
        if std and std not in keep.values():
            keep[col] = std
    out = df[list(keep)].rename(columns=keep).copy()
    for c in out.columns:
        out[c] = out[c].map(clean)
    if "recipe_id" in out.columns:
        # merged cells leave the id only on the first row → fill down
        out["recipe_id"] = out["recipe_id"].replace("", pd.NA).ffill().fillna("")
    return out


def _split_qty(df: pd.DataFrame) -> pd.DataFrame:
    """'5 ส่วน' in one cell → qty 5, unit ส่วน (only when no unit column)."""
    if "qty_original" not in df.columns:
        return df
    if "unit_original" not in df.columns or (df["unit_original"] == "").all():
        m = df["qty_original"].str.translate(_THAI_DIGITS).str.extract(_QTY)
        has = m[0].notna()
        df.loc[has, "unit_original"] = m.loc[has, 1].str.strip()
        df.loc[has, "qty_original"] = m.loc[has, 0]
    return df


def _explode(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.assign(**{col: df[col].str.split(SPLIT, regex=True)}).explode(col)
    df[col] = df[col].map(clean)
    return df[df[col] != ""]


def read_sources(files: list[tuple[str, bytes | Path]]) -> Imported:
    parts: dict[str, list[pd.DataFrame]] = {k: [] for k in SCHEMA}
    sources, skipped = [], {}

    for fname, src in files:
        raw = src.read_bytes() if isinstance(src, Path) else (src.getvalue() if hasattr(src, "getvalue") else src)
        try:
            frames = _frames(fname, raw)
        except Exception as e:
            sources.append(Source(fname, ["skipped"], "", 0, str(e)))
            continue
        for name, frame in frames:
            df = _standardise(frame)
            cols = set(df.columns)
            kinds = []
            if "recipe_id" not in cols:
                # reference tables
                if {"identity", "availability"} & cols and "herb_id" in cols:
                    parts["herb_grades"].append(df); kinds.append("herb_grades")
                elif "warning_text" in cols and "herb_id" in cols:
                    parts["herb_safety"].append(df); kinds.append("herb_safety")
                elif "group_name" in cols and "herb_id" in cols:
                    parts["herb_groups"].append(df); kinds.append("herb_groups")
                elif "alias" in cols and "herb_id" in cols:
                    parts["herb_synonyms"].append(df); kinds.append("herb_synonyms")
                elif "herb_id" in cols or "std_name_th" in cols:
                    parts["herbs"].append(df); kinds.append("herbs")
                sources.append(Source(name, kinds or ["skipped"], "", len(df),
                                      "" if kinds else f"ไม่รู้จักคอลัมน์: {', '.join(map(str, frame.columns))[:120]}"))
                continue

            file_book = _book_from_name(name)
            ids_book = df["recipe_id"].map(book_of)
            if "book" in cols:
                ids_book = ids_book.where(ids_book != "", df["book"].str.upper())
            df["book"] = ids_book.where(ids_book != "", file_book)
            df = df[df["recipe_id"] != ""]
            other = df[~df["book"].isin(BOOKS)]
            for b, n in other.groupby("book").size().items():
                skipped[b or "(ไม่ทราบ)"] = skipped.get(b or "(ไม่ทราบ)", 0) + int(n)
            df = df[df["book"].isin(BOOKS)]

            if "herb" in cols:
                h = _split_qty(df[df["herb"] != ""].rename(columns={"herb": "herb_name_original"}).copy())
                parts["recipe_herbs"].append(h)
                if "sci_name" in cols:  # remember scientific names for the herb list
                    parts.setdefault("_sci", []).append(h[["herb_name_original", "sci_name"]])
                kinds.append("recipe_herbs")
            if "symptom" in cols:
                s = _explode(df.rename(columns={"symptom": "symptom_original"}), "symptom_original")
                parts["recipe_symptoms"].append(s); kinds.append("recipe_symptoms")
            if "indication" in cols:
                parts["recipe_indications"].append(_explode(df, "indication")); kinds.append("recipe_indications")
            if set(RECIPE_FIELDS) & cols or not kinds:
                parts["recipes"].append(df); kinds.append("recipes")
            books = ", ".join(sorted(df["book"].unique())) or file_book or "-"
            sources.append(Source(name, kinds, books, len(df)))

    tables = {}
    for name, cols in SCHEMA.items():
        frames = parts.get(name) or []
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=cols)
        tables[name] = df.reindex(columns=cols + [c for c in ("book",) if c in df.columns and c not in cols]) \
            .fillna("")
    sci = pd.concat(parts["_sci"], ignore_index=True) if parts.get("_sci") else pd.DataFrame(
        columns=["herb_name_original", "sci_name"])
    tables["_sci"] = sci
    return Imported(tables, sources, skipped)


def _recipes_from(imp: Imported) -> pd.DataFrame:
    """One row per recipe: first non-empty value per field; stubs for ids only seen in herbs/symptoms."""
    t = imp.tables
    rec = t["recipes"].copy()
    ids = []
    for name in ("recipe_herbs", "recipe_symptoms", "recipe_indications"):
        if "book" in t[name].columns:
            ids.append(t[name][["recipe_id", "book"]])
    if ids:
        rec = pd.concat([rec] + ids, ignore_index=True).fillna("")
    rec = rec.replace("", pd.NA).groupby("recipe_id", as_index=False).first().fillna("")
    rec["review_status"] = rec["review_status"].replace("", "pending")
    return rec.reindex(columns=SCHEMA["recipes"]).fillna("")


def _qty_percent(rh: pd.DataFrame) -> pd.DataFrame:
    """% of recipe only when every herb in the recipe has a number in the SAME unit.

    Ancient units (บาท, สลึง, ส่วน …) are not converted here: the conversion
    rule must come from the team. The rule used is written to qty_rule.
    """
    rh = rh.copy()
    num = pd.to_numeric(rh["qty_original"].str.translate(_THAI_DIGITS).str.replace(",", ""), errors="coerce")
    rh["_num"] = num
    for rid, g in rh.groupby("recipe_id"):
        if g["_num"].notna().all() and g["unit_original"].nunique() == 1 and g["_num"].sum() > 0:
            rh.loc[g.index, "qty_percent"] = (g["_num"] / g["_num"].sum() * 100).round(1).astype(str)
            rh.loc[g.index, "qty_rule"] = f"สัดส่วนจากหน่วยเดียวกัน ({g['unit_original'].iloc[0] or 'ไม่ระบุหน่วย'})"
    return rh.drop(columns="_num")


@dataclass
class Check:
    ok: bool
    detail: str
    blocking: bool = False
    rows: pd.DataFrame | None = None


def build_tables(imp: Imported, keep_reference: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[Check]]:
    t = imp.tables
    checks: list[Check] = []
    rec = _recipes_from(imp)
    rh = t["recipe_herbs"].drop(columns="book", errors="ignore").drop_duplicates(["recipe_id", "herb_name_original"])
    rh = _qty_percent(rh.reindex(columns=SCHEMA["recipe_herbs"]).fillna(""))
    sym = t["recipe_symptoms"].drop(columns="book", errors="ignore").drop_duplicates(["recipe_id", "symptom_original"])
    ind = t["recipe_indications"].drop(columns="book", errors="ignore").drop_duplicates()

    out = {"recipes": rec, "recipe_herbs": rh, "recipe_symptoms": sym.reindex(columns=SCHEMA["recipe_symptoms"]),
           "recipe_indications": ind.reindex(columns=SCHEMA["recipe_indications"])}
    # reference tables: new upload wins, else keep what we have
    for name in ("herbs", "herb_synonyms", "herb_groups", "herb_grades", "herb_safety", "evidence"):
        out[name] = t[name] if not t[name].empty else keep_reference.get(name, pd.DataFrame(columns=SCHEMA[name]))
    out = {k: v.fillna("") for k, v in out.items()}

    # ---- checks ----
    checks.append(Check(not rec.empty, f"พบตำรับ {len(rec):,} ตำรับ", blocking=rec.empty))
    if not rec.empty:
        checks.append(Check(True, " · ".join(f"{b} {int((rec['book'] == b).sum())} ตำรับ" for b in BOOKS)))
    for b, n in imp.skipped_books.items():
        checks.append(Check(False, f"ข้าม {n} แถวของ {b} (ไม่อยู่ใน {', '.join(BOOKS)})"))
    no_herb = rec[~rec["recipe_id"].isin(rh["recipe_id"])]
    if not no_herb.empty:
        by = no_herb["book"].value_counts().to_dict()
        checks.append(Check(False, f"ตำรับที่ยังไม่แยกสมุนไพร {len(no_herb)} ตำรับ ({by}) → ไม่เข้า Apriori/คัดเลือก",
                            rows=no_herb[["recipe_id", "book"]]))
    no_sym = rec[~rec["recipe_id"].isin(sym["recipe_id"]) & ~rec["recipe_id"].isin(ind["recipe_id"])]
    if not no_sym.empty:
        checks.append(Check(False, f"ตำรับที่ยังไม่มีอาการ/ข้อบ่งใช้ {len(no_sym)} ตำรับ",
                            rows=no_sym[["recipe_id", "book"]]))
    if ind.empty:
        checks.append(Check(False, "ยังไม่มีคอลัมน์ข้อบ่งใช้ (INDICATION) แยกจากอาการ"))
    known = set(out["herbs"]["herb_id"]) | set(out["herbs"]["std_name_th"])
    syn = out["herb_synonyms"]
    known |= set(syn.loc[syn["review_status"] == "verified", "alias"])
    known |= set(out["herb_groups"].loc[out["herb_groups"]["review_status"] == "verified", "group_name"])
    unknown = sorted(set(rh["herb_name_original"]) - known)
    checks.append(Check(not unknown, f"ชื่อสมุนไพรที่ยังไม่ยืนยัน {len(unknown)} ชื่อ (จะแสดงเป็น รอตรวจสอบ)",
                        rows=pd.DataFrame({"herb_name_original": unknown})))
    long_sym = sym[sym["symptom_original"].str.len() > 40]
    if not long_sym.empty:
        checks.append(Check(False, f"อาการยาวผิดปกติ {len(long_sym)} แถว (อาจเป็นข้อความทั้งย่อหน้า)", rows=long_sym))
    return out, checks


def suggested_herbs(imp: Imported) -> pd.DataFrame:
    """Distinct herb names with their most common scientific name. For the review queue only:
    nothing here becomes a standard herb until a reviewer approves it."""
    sci = imp.tables["_sci"]
    sci = sci[sci["sci_name"] != ""]
    return (sci.groupby("herb_name_original")["sci_name"].agg(lambda s: s.value_counts().index[0])
            .rename("sci_name").reset_index())


def publish(tables: dict[str, pd.DataFrame], version: str, note: str = "", is_sample: bool = False,
            data_dir: Path = DATA_DIR) -> None:
    """Archive the current dataset, write the new one."""
    data_dir = Path(data_dir)
    meta_path = data_dir / "dataset.json"
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        arch = data_dir / "versions" / str(old.get("version", "old"))
        arch.mkdir(parents=True, exist_ok=True)
        for p in data_dir.glob("*.csv"):
            shutil.copy2(p, arch / p.name)
        shutil.copy2(meta_path, arch / "dataset.json")
    for name, df in tables.items():
        if name in SCHEMA and name != "review_log":
            save_table(name, df, data_dir)
    rec = tables["recipes"]
    meta = {"version": version, "updated": dt.date.today().isoformat(), "is_sample": is_sample, "note": note,
            "books": {b: int((rec["book"] == b).sum()) for b in BOOKS}}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def current_reference(data_dir: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Reference tables to carry into a new import. Sample (จำลอง) references are never
    carried into real data: then only data/reference/ (sourced defaults) is used."""
    data_dir = Path(data_dir)
    meta = data_dir / "dataset.json"
    is_sample = meta.exists() and json.loads(meta.read_text(encoding="utf-8")).get("is_sample")
    src = data_dir / "reference" if is_sample else data_dir
    return {n: read_table(n, src)[0] for n in ("herbs", "herb_synonyms", "herb_groups", "herb_grades",
                                                 "herb_safety", "evidence")}


def list_versions(data_dir: Path = DATA_DIR) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((Path(data_dir) / "versions").glob("*/dataset.json"), reverse=True)]
