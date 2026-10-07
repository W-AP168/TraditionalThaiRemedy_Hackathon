"""Import the team's data (Excel workbook and/or CSVs) into data/.

    python prepare_data.py data/raw                       # check only
    python prepare_data.py data/raw --version 0.2         # check + publish
    python prepare_data.py team.xlsx herbs_RM.csv --version 0.3

Files are recognised by their columns (see core/ingest.py). Reference tables
(herb list, synonyms, คณาเภสัช, grades, safety) are taken from the upload when
present, otherwise kept from the current dataset. Sample (จำลอง) reference
tables are never carried into real data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.ingest import build_tables, current_reference, publish, read_sources


def collect(paths: list[str]) -> list[tuple[str, Path]]:
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out += [(f.name, f) for f in sorted(p.iterdir()) if f.suffix.lower() in (".csv", ".xlsx", ".xls")]
        elif p.exists():
            out.append((p.name, p))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", default=["data/raw"])
    ap.add_argument("--version", help="publish as this data version (omit = check only)")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    files = collect(args.paths)
    if not files:
        raise SystemExit(f"ไม่พบไฟล์ใน {args.paths}")
    imp = read_sources(files)
    print("ไฟล์/ชีตที่อ่าน:")
    for s in imp.sources:
        print(f"  {s.name[:50]:50s} {'+'.join(s.kinds):40s} {s.book:12s} {s.rows:6d} แถว {s.note}")
    tables, checks = build_tables(imp, current_reference())
    print()
    for c in checks:
        print(("✓ " if c.ok else ("⛔ " if c.blocking else "⚠️ ")) + c.detail)
    if not args.version:
        print("\n(ตรวจอย่างเดียว ใส่ --version เพื่อเผยแพร่)")
        return
    if any(c.blocking for c in checks):
        raise SystemExit("มีข้อผิดพลาดที่ต้องแก้ก่อนเผยแพร่")
    publish(tables, args.version, args.note)
    print(f"\n✅ เผยแพร่ข้อมูล v{args.version} แล้ว")


if __name__ == "__main__":
    main()
