"""Import the team's cleaned CSVs into the website.

1. Put the CSV files in data/raw/ (any names; see core/team_csv.py for how
   each file is recognised). Optional: a synonym file with "synonym" or
   "ชื่อพ้อง" in its name (2 columns: ชื่อพ้อง, ชื่อหลัก).
2. Run:
       python -m preprocessing.import_team_csvs                 # check only
       python -m preprocessing.import_team_csvs --version 0.2   # check + publish

Safety notes and missing scientific names come from data/reference/herb_reference.csv.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from core.data_loader import DATA_DIR
from core.team_csv import TeamData, quality_notes, read_files, read_folder, to_app_tables
from preprocessing.prepare_data import Report, prepare, publish

RAW_DIR = DATA_DIR / "raw"
REF_DIR = DATA_DIR / "reference"


def _ref(name: str) -> pd.DataFrame | None:
    p = REF_DIR / name
    return pd.read_csv(p, dtype=str, keep_default_na=False) if p.exists() else None


def build(td: TeamData, data_dir: Path = DATA_DIR) -> tuple[Report, list[str]]:
    tables = to_app_tables(td, _ref("herb_reference.csv"), _ref("herb_synonyms.csv"))
    rep = prepare(tables, data_dir)
    return rep, quality_notes(td)


def import_files(files: list[tuple[str, object]], data_dir: Path = DATA_DIR) -> tuple[TeamData, Report, list[str]]:
    td = read_files(files)
    rep, notes = build(td, data_dir)
    return td, rep, notes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", default=str(RAW_DIR))
    ap.add_argument("--version", help="publish as this dataset version (omit to only check)")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    td = read_folder(args.folder)
    print("ไฟล์ที่พบ:")
    for f in td.files:
        print(f"  {f.name:40s} {f.kind:9s} {f.book:12s} {f.rows:6d} แถว {f.note}")
    rep, notes = build(td)
    print(f"\n{td.herbs['recipe_id'].nunique()} ตำรับ · {td.herbs['herb'].nunique()} ชื่อสมุนไพร (ก่อนรวมชื่อพ้อง) · "
          f"{td.symptoms['symptom'].nunique()} อาการ")
    for n in notes:
        print("⚠️", n)
    for c in rep.checks:
        print(("✓ " if c.ok else "✗ ") + c.detail)
    if not args.version:
        print("\n(ตรวจอย่างเดียว ใส่ --version เพื่อเผยแพร่)")
        return
    if not rep.can_publish:
        raise SystemExit("มีข้อผิดพลาดที่ต้องแก้ก่อนเผยแพร่")
    publish(rep, args.version, args.note)
    print(f"\n✅ เผยแพร่ dataset v{args.version} แล้ว เปิดเว็บใหม่ได้เลย")


if __name__ == "__main__":
    main()
