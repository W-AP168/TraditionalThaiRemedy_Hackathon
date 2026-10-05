"""Read the team's cleaned CSVs, whatever the files are called.

Each CSV is recognised by its COLUMNS, not its name:
  has a herb column            → herb rows     (1 row = 1 recipe × 1 herb)
  has a symptom column         → symptom rows  (1 row = 1 recipe × 1 symptom)
  has both (old one-table CSV) → both
The scripture comes from the recipe id prefix (WRO133/1 → WRO), or from the
file name when the id has no known prefix. Rows from scriptures not in
SCRIPTURES (e.g. RM) are skipped and reported.

Used by the website (admin page, preprocessing/import_team_csvs.py) and by
team_scripts/ (Application_search_remedy.py, Database.py).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# ---- the 3 scriptures in this project: add/remove here ----
SCRIPTURE_NAMES = {
    "WRO": "คัมภีร์จารึกวัดราชโอรสาราม",
    "NR": "คัมภีร์โอสถพระนารายณ์",
    "WP": "จารึกตำรายาวัดโพธิ์",
}
SCRIPTURES = list(SCRIPTURE_NAMES)

# column name variants → standard name (compared after trimming spaces)
ALIASES = {
    "recipe_id": ["รหัสตำรับ", "รหัสตำรับยา", "รหัส", "recipe_id", "recipe", "id"],
    "herb": ["ชื่อสมุนไพร", "ชื่อสมุนไพรตามคัมภีร์", "ชื่อข้อมูลยา", "สมุนไพร", "herb", "herb_raw", "herb_name"],
    "sci_name": ["ชื่อวิทยาศาสตร์", "ชื่อทยาศาสตร์", "ชื่อวิทย์", "sci_name", "scientific_name"],
    "symptom": ["อาการ", "อาการต่างๆ", "อาการต่าง ๆ", "สรรพคุณ", "symptom", "symptoms"],
    "amount": ["ปริมาณ", "ส่วน", "amount"],
    "recipe_name": ["ชื่อตำรับ", "ชื่อตำรับยา", "name_th", "recipe_name"],
    "form": ["รูปแบบยา", "รูปแบบ", "form"],
    "original_text": ["ข้อความต้นฉบับ", "ข้อความเดิม", "ข้อความจากคัมภีร์", "original_text"],
    "page_ref": ["หน้า", "เลขหน้า", "page", "page_ref"],
}
_LOOKUP = {a.strip().lower(): std for std, names in ALIASES.items() for a in names}

# several symptoms in one cell: split on , ; / newline (not on spaces: Thai symptoms contain spaces)
SYMPTOM_SEPARATORS = r"[,;/\n、]+"
MISSING = {"", "-", "nan", "none", "ไม่ระบุ", "null"}
_PREFIX = re.compile(r"^([A-Za-z]+)")


def clean_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = " ".join(str(value).split())
    return "" if text.lower() in MISSING else text


def book_of(recipe_id: str) -> str:
    m = _PREFIX.match(recipe_id or "")
    return m.group(1).upper() if m else ""


def _book_from_name(name: str) -> str:
    stem = Path(name).stem.upper()
    # longest code first so "WRO" wins over a shorter code it contains
    for code in sorted(SCRIPTURES, key=len, reverse=True):
        if re.search(rf"(^|[^A-Z]){code}([^A-Z]|$)", stem):
            return code
    return ""


@dataclass
class FileInfo:
    name: str
    kind: str          # "herbs", "symptoms", "both", "synonyms", "skipped"
    book: str
    rows: int
    note: str = ""


@dataclass
class TeamData:
    herbs: pd.DataFrame        # book, recipe_id, herb, sci_name, amount
    symptoms: pd.DataFrame     # book, recipe_id, symptom
    recipes: pd.DataFrame      # book, recipe_id, recipe_name, form, original_text, page_ref
    synonyms: dict[str, str]
    files: list[FileInfo] = field(default_factory=list)
    skipped_books: dict[str, int] = field(default_factory=dict)


def _read_csv(src) -> pd.DataFrame:
    raw = src.read_bytes() if isinstance(src, Path) else (src.getvalue() if hasattr(src, "getvalue") else src)
    for enc in ("utf-8-sig", "cp874", "tis-620"):  # cp874 = Thai Windows Excel export
        try:
            return pd.read_csv(io.BytesIO(raw), dtype=str, encoding=enc, keep_default_na=False)
        except UnicodeDecodeError:
            continue
    raise ValueError("อ่านไฟล์ไม่ได้: ไม่ใช่ UTF-8 หรือ Thai (cp874)")


def _standardise(df: pd.DataFrame) -> pd.DataFrame:
    rename, seen = {}, set()
    for col in df.columns:
        std = _LOOKUP.get(str(col).strip().lower())
        if std and std not in seen:
            rename[col] = std
            seen.add(std)
    df = df.rename(columns=rename)[list(rename.values())].copy()
    for col in df.columns:
        df[col] = df[col].map(clean_text)
    if "recipe_id" in df.columns:
        # merged cells in Excel leave the id only on the first row → fill down
        df["recipe_id"] = df["recipe_id"].replace("", pd.NA).ffill().fillna("")
    return df


def read_files(files: list[tuple[str, object]]) -> TeamData:
    """files: (file name, Path | bytes | uploaded file) pairs."""
    herb_parts, sym_parts, rec_parts, infos = [], [], [], []
    synonyms: dict[str, str] = {}
    skipped: dict[str, int] = {}

    for name, src in files:
        if not name.lower().endswith(".csv"):
            continue
        try:
            raw = _read_csv(src)
        except Exception as e:  # unreadable file: report, keep going
            infos.append(FileInfo(name, "skipped", "", 0, str(e)))
            continue

        if "synonym" in name.lower() or "ชื่อพ้อง" in name:
            pairs = raw.iloc[:, :2].map(clean_text)
            for a, b in pairs.itertuples(index=False):
                if a and b and a != b:
                    synonyms[a] = b
            infos.append(FileInfo(name, "synonyms", "", len(pairs)))
            continue

        df = _standardise(raw)
        has_herb, has_sym = "herb" in df.columns, "symptom" in df.columns
        if "recipe_id" not in df.columns or not (has_herb or has_sym):
            infos.append(FileInfo(name, "skipped", "", len(df),
                                  f"ไม่พบคอลัมน์รหัสตำรับ + สมุนไพร/อาการ (มี: {', '.join(map(str, raw.columns))})"))
            continue

        file_book = _book_from_name(name)
        ids_book = df["recipe_id"].map(book_of)
        # trust the id prefix; use the file name only for ids without one (e.g. "001/1")
        df["book"] = ids_book.where(ids_book != "", file_book)
        df = df[df["recipe_id"] != ""]
        other = df[~df["book"].isin(SCRIPTURES)]
        for b, n in other.groupby(ids_book.reindex(other.index)).size().items():
            skipped[b or "(ไม่ทราบ)"] = skipped.get(b or "(ไม่ทราบ)", 0) + int(n)
        df = df[df["book"].isin(SCRIPTURES)]

        if has_herb:
            cols = ["book", "recipe_id", "herb"] + [c for c in ("sci_name", "amount") if c in df.columns]
            herb_parts.append(df.loc[df["herb"] != "", cols])
        if has_sym:
            s = df[["book", "recipe_id", "symptom"]].copy()
            s["symptom"] = s["symptom"].str.split(SYMPTOM_SEPARATORS, regex=True)
            s = s.explode("symptom")
            s["symptom"] = s["symptom"].map(clean_text)
            sym_parts.append(s[s["symptom"] != ""])
        extra = [c for c in ("recipe_name", "form", "original_text", "page_ref") if c in df.columns]
        if extra:
            rec_parts.append(df[["book", "recipe_id"] + extra])

        books = ", ".join(sorted(df["book"].unique())) or file_book or "-"
        kind = "both" if has_herb and has_sym else ("herbs" if has_herb else "symptoms")
        infos.append(FileInfo(name, kind, books, len(df)))

    def cat(parts, cols):
        out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
        for c in cols:
            if c not in out.columns:
                out[c] = ""
        return out[cols].fillna("")

    herbs = cat(herb_parts, ["book", "recipe_id", "herb", "sci_name", "amount"])
    if synonyms:
        herbs["herb"] = herbs["herb"].map(lambda h: synonyms.get(h, h))
    herbs = herbs.drop_duplicates(["recipe_id", "herb"]).reset_index(drop=True)
    symptoms = cat(sym_parts, ["book", "recipe_id", "symptom"]).drop_duplicates(["recipe_id", "symptom"])
    recipes = cat(rec_parts, ["book", "recipe_id", "recipe_name", "form", "original_text", "page_ref"])
    # one row per recipe: first non-empty value of each column
    recipes = recipes.replace("", pd.NA).groupby("recipe_id", as_index=False).first().fillna("")
    return TeamData(herbs, symptoms.reset_index(drop=True), recipes, synonyms, infos, skipped)


def read_folder(folder: str | Path) -> TeamData:
    folder = Path(folder)
    return read_files([(p.name, p) for p in sorted(folder.glob("*.csv"))])


def quality_notes(td: TeamData) -> list[str]:
    """Things worth fixing in the data before trusting the analysis."""
    notes = []
    for b, n in td.skipped_books.items():
        notes.append(f"ข้าม {n} แถวของคัมภีร์ {b} (ไม่อยู่ใน {', '.join(SCRIPTURES)})")
    h_ids, s_ids = set(td.herbs["recipe_id"]), set(td.symptoms["recipe_id"])
    if h_ids - s_ids:
        notes.append(f"ตำรับที่มีสมุนไพรแต่ไม่มีอาการ {len(h_ids - s_ids)} ตำรับ เช่น {sorted(h_ids - s_ids)[:5]}")
    if s_ids - h_ids:
        notes.append(f"ตำรับที่มีอาการแต่ไม่มีสมุนไพร {len(s_ids - h_ids)} ตำรับ เช่น {sorted(s_ids - h_ids)[:5]}")
    sci = td.herbs[td.herbs["sci_name"] != ""].groupby("herb")["sci_name"].nunique()
    if (sci > 1).any():
        notes.append(f"สมุนไพรที่มีชื่อวิทยาศาสตร์มากกว่า 1 ชื่อ: {sci[sci > 1].index.tolist()[:10]}")
    long_sym = td.symptoms[td.symptoms["symptom"].str.len() > 40]
    if not long_sym.empty:
        notes.append(f"อาการที่ยาวผิดปกติ {len(long_sym)} แถว (อาจเป็นข้อความสรรพคุณทั้งย่อหน้า ควรแยกเป็นอาการ)")
    return notes


def to_app_tables(td: TeamData, reference_herbs: pd.DataFrame | None = None,
                  reference_synonyms: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Convert to the website's data model (same tables as data/*.csv)."""
    ids = sorted(set(td.herbs["recipe_id"]) | set(td.symptoms["recipe_id"]))
    book = pd.concat([td.herbs[["recipe_id", "book"]], td.symptoms[["recipe_id", "book"]]]).drop_duplicates("recipe_id")
    pres = pd.DataFrame({"recipe_id": ids}).merge(book, on="recipe_id", how="left")
    pres = pres.merge(td.recipes.drop(columns="book", errors="ignore"), on="recipe_id", how="left").fillna("")
    first_sym = td.symptoms.groupby("recipe_id")["symptom"].first()
    pres["name_th"] = [
        n or (f"ตำรับแก้{first_sym[r]}" if r in first_sym.index else r)
        for r, n in zip(pres["recipe_id"], pres["recipe_name"])
    ]
    prescriptions = pres.rename(columns={"book": "scripture_id"})[
        ["recipe_id", "scripture_id", "name_th", "form", "original_text", "page_ref"]]

    ingredients = td.herbs.rename(columns={"herb": "herb_raw"})[["recipe_id", "herb_raw", "amount"]]
    symptoms = td.symptoms[["recipe_id", "symptom"]]

    syn = dict(td.synonyms)
    if reference_synonyms is not None:
        for a, b in reference_synonyms[["synonym", "herb_id"]].itertuples(index=False):
            syn.setdefault(a, b)
    synonyms = pd.DataFrame(sorted(syn.items()), columns=["synonym", "herb_id"])
    canon = td.herbs.assign(herb=td.herbs["herb"].map(lambda h: syn.get(h, h)))

    # herbs: scientific name = most common one in the team data, safety from the reference list
    sci = (canon[canon["sci_name"] != ""].groupby("herb")["sci_name"]
           .agg(lambda s: s.value_counts().index[0]))
    herbs = pd.DataFrame({"herb_id": sorted(canon["herb"].unique())})
    herbs["sci_name"] = herbs["herb_id"].map(sci).fillna("")
    herbs["safety_level"], herbs["safety_note"] = "none", ""
    if reference_herbs is not None and not reference_herbs.empty:
        ref = reference_herbs.set_index("herb_id")
        known = herbs["herb_id"].isin(ref.index)
        for col in ("safety_level", "safety_note"):
            if col in ref.columns:
                herbs.loc[known, col] = herbs.loc[known, "herb_id"].map(ref[col]).fillna("")
        missing_sci = known & (herbs["sci_name"] == "")
        herbs.loc[missing_sci, "sci_name"] = herbs.loc[missing_sci, "herb_id"].map(ref["sci_name"]).fillna("")
        herbs["safety_level"] = herbs["safety_level"].replace("", "none")


    scriptures = pd.DataFrame(
        [(k, v, "") for k, v in SCRIPTURE_NAMES.items()], columns=["scripture_id", "name_th", "name_en"])
    return {
        "scriptures": scriptures,
        "prescriptions": prescriptions,
        "ingredients": ingredients,
        "symptoms": symptoms,
        "herbs": herbs,
        "herb_synonyms": synonyms,
        # no symptom groups in the team data; the symptom page groups by co-occurrence instead
        "symptom_groups": pd.DataFrame(columns=["symptom", "symptom_group"]),
    }
