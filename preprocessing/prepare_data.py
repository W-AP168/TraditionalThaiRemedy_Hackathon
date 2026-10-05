"""Excel → validated CSVs → published dataset version.

Pipeline (same steps the admin page shows):
  1 validate sheets   2 normalize names   3 apply synonym dictionary
  4 check duplicates  5 check missing values   6 publish new version

Excel layout: one sheet per table, same names and columns as data/*.csv:
  prescriptions (recipe_id, scripture_id, name_th, [form, original_text, page_ref])
  ingredients   (recipe_id, herb_raw, [amount])
  symptoms      (recipe_id, symptom)
  herbs, herb_synonyms, scriptures, symptom_groups   (optional: current
  files in data/ are kept when the sheet is absent)

    python -m preprocessing.prepare_data path/to/file.xlsx --version 1.0
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from core.data_loader import DATA_DIR, REQUIRED_FILES, apply_synonyms, normalize_name

REQUIRED_SHEETS = ["prescriptions", "ingredients", "symptoms"]
OPTIONAL_SHEETS = ["herbs", "herb_synonyms", "scriptures", "symptom_groups"]


@dataclass(eq=False)
class Check:
    step: str
    ok: bool
    detail: str = ""
    rows: pd.DataFrame | None = None


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def blocking(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and c.step in ("validate", "duplicates")]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and c.step not in ("validate", "duplicates")]

    @property
    def can_publish(self) -> bool:
        return bool(self.tables) and not self.blocking


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].map(normalize_name)
    return df


def prepare(sheets: dict[str, pd.DataFrame], data_dir: Path = DATA_DIR) -> Report:
    rep = Report()

    # 1 validate sheets + columns
    missing = [s for s in REQUIRED_SHEETS if s not in sheets]
    if missing:
        rep.checks.append(Check("validate", False, "ไม่พบชีต: " + ", ".join(missing)))
        return rep
    tables: dict[str, pd.DataFrame] = {}
    for name in REQUIRED_SHEETS + OPTIONAL_SHEETS:
        if name in sheets:
            tables[name] = _clean(sheets[name].astype(str).replace({"nan": "", "None": ""}))
        elif (data_dir / f"{name}.csv").exists():
            tables[name] = pd.read_csv(data_dir / f"{name}.csv", dtype=str, keep_default_na=False)
    bad_cols = []
    for name, cols in REQUIRED_FILES.items():
        if name in tables:
            lack = [c for c in cols if c not in tables[name].columns]
            if lack:
                bad_cols.append(f"{name}: {', '.join(lack)}")
        else:
            bad_cols.append(f"{name}: ไม่มีทั้งชีตและไฟล์เดิม")
    rep.checks.append(Check("validate", not bad_cols, "; ".join(bad_cols) or "ชีตและคอลัมน์ครบ"))
    if bad_cols:
        return rep

    # 2 + 3 normalize names, apply synonyms
    ing = tables["ingredients"]
    ing["herb_id"] = apply_synonyms(ing["herb_raw"], tables["herb_synonyms"])
    renamed = int((ing["herb_id"] != ing["herb_raw"]).sum())
    rep.checks.append(Check("synonyms", True, f"แปลงชื่อพ้องเป็นชื่อหลัก {renamed} แถว"))

    known = set(tables["herbs"]["herb_id"])
    unmapped = ing[(ing["herb_id"] != "") & ~ing["herb_id"].isin(known)]
    unmapped_names = unmapped.groupby("herb_id").size().rename("rows").reset_index()
    rep.checks.append(Check(
        "unmapped", unmapped_names.empty,
        f"ชื่อสมุนไพรที่ไม่อยู่ใน herbs/ชื่อพ้อง {len(unmapped_names)} ชื่อ", unmapped_names,
    ))

    # 4 duplicates
    dup_ids = tables["prescriptions"][tables["prescriptions"]["recipe_id"].duplicated(keep=False)]
    rep.checks.append(Check("duplicates", dup_ids.empty, f"รหัสตำรับซ้ำ {dup_ids['recipe_id'].nunique()} รหัส", dup_ids))
    dup_ing = ing[ing.duplicated(["recipe_id", "herb_id"], keep=False) & (ing["herb_id"] != "")]
    rep.checks.append(Check("dup_ingredients", dup_ing.empty,
                            f"สมุนไพรซ้ำในตำรับเดียวกัน {len(dup_ing)} แถว (จะนับครั้งเดียว)", dup_ing))

    # 5 missing values
    empty_herb = ing[ing["herb_raw"] == ""]
    rep.checks.append(Check("missing_herb", empty_herb.empty, f"ชื่อสมุนไพรว่าง {len(empty_herb)} แถว", empty_herb))
    ids = set(tables["prescriptions"]["recipe_id"])
    orphan = pd.concat([
        ing.loc[~ing["recipe_id"].isin(ids), ["recipe_id"]].assign(sheet="ingredients"),
        tables["symptoms"].loc[~tables["symptoms"]["recipe_id"].isin(ids), ["recipe_id"]].assign(sheet="symptoms"),
    ]).drop_duplicates()
    rep.checks.append(Check("orphans", orphan.empty, f"รหัสตำรับที่ไม่มีใน prescriptions {len(orphan)} รายการ", orphan))
    no_herbs = ids - set(ing.loc[ing["herb_id"] != "", "recipe_id"])
    rep.checks.append(Check("no_herbs", not no_herbs, f"ตำรับที่ไม่มีสมุนไพรเลย {len(no_herbs)} ตำรับ",
                            pd.DataFrame({"recipe_id": sorted(no_herbs)})))

    tables["ingredients"] = ing.drop(columns="herb_id")
    rep.tables = tables
    return rep


def read_excel(file) -> dict[str, pd.DataFrame]:
    return pd.read_excel(file, sheet_name=None, dtype=str)


def current_version(data_dir: Path = DATA_DIR) -> dict:
    p = data_dir / "dataset.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def list_versions(data_dir: Path = DATA_DIR) -> list[dict]:
    out = []
    for meta in sorted((data_dir / "versions").glob("*/dataset.json"), reverse=True):
        out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out


def publish(rep: Report, version: str, note: str = "", data_dir: Path = DATA_DIR, is_sample: bool = False) -> Path:
    """Archive the current data, then write the new tables as the live dataset."""
    if not rep.can_publish:
        raise ValueError("report has blocking errors")
    data_dir = Path(data_dir)
    old = current_version(data_dir)
    if old.get("version"):
        archive = data_dir / "versions" / old["version"]
        archive.mkdir(parents=True, exist_ok=True)
        for p in data_dir.glob("*.csv"):
            shutil.copy2(p, archive / p.name)
        shutil.copy2(data_dir / "dataset.json", archive / "dataset.json")
    for name, df in rep.tables.items():
        df.to_csv(data_dir / f"{name}.csv", index=False)
    meta = {
        "version": version,
        "updated": dt.date.today().isoformat(),
        "is_sample": is_sample,
        "note": note,
        "n_recipes": int(rep.tables["prescriptions"]["recipe_id"].nunique()),
    }
    (data_dir / "dataset.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return data_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("excel")
    ap.add_argument("--version", required=True)
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    rep = prepare(read_excel(args.excel))
    for c in rep.checks:
        print(("✓ " if c.ok else "✗ ") + c.detail)
    if not rep.can_publish:
        raise SystemExit("blocking errors: fix the Excel and run again")
    publish(rep, args.version, args.note)
    print(f"published dataset v{args.version}")


if __name__ == "__main__":
    main()
