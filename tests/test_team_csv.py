import pandas as pd

from core.team_csv import quality_notes, read_files, read_folder, to_app_tables
from preprocessing.prepare_data import prepare


def csv(df: pd.DataFrame, encoding: str = "utf-8-sig") -> bytes:
    return df.to_csv(index=False).encode(encoding)


def test_files_recognised_by_columns_not_names():
    herbs = pd.DataFrame({"รหัสตำรับยา": ["WRO001/1", "", "NR002/1"],  # blank = merged cell
                          "ชื่อสมุนไพรตามคัมภีร์": [" ขิง ", "ดีปลี", "ขิง"]})
    sym = pd.DataFrame({"รหัสตำรับ": ["WRO001/1", "NR002/1"], "สรรพคุณ": ["ไข้, ไอ", "ท้องอืด"]})
    td = read_files([("final v2 (1).csv", csv(herbs)), ("whatever.csv", csv(sym))])
    kinds = {f.name: f.kind for f in td.files}
    assert kinds == {"final v2 (1).csv": "herbs", "whatever.csv": "symptoms"}
    # merged cell filled down, spaces trimmed
    assert set(td.herbs.query("recipe_id == 'WRO001/1'")["herb"]) == {"ขิง", "ดีปลี"}
    # "ไข้, ไอ" split into two symptoms
    assert set(td.symptoms.query("recipe_id == 'WRO001/1'")["symptom"]) == {"ไข้", "ไอ"}
    assert set(td.herbs["book"]) == {"WRO", "NR"}


def test_rm_rows_skipped_and_old_combined_file_read():
    old = pd.DataFrame({"รหัสตำรับ": ["WP001/1", "WP001/1", "RM009/1"],
                        "ชื่อสมุนไพร": ["ขิง", "ดีปลี", "ขิง"],
                        "อาการต่างๆ": ["ไข้", "ไข้", "ไข้"]})
    td = read_files([("clean_database_WP.csv", csv(old))])
    assert td.files[0].kind == "both"
    assert set(td.herbs["recipe_id"]) == {"WP001/1"}
    # symptom repeated on every herb row is counted once per recipe
    assert len(td.symptoms) == 1
    assert td.skipped_books == {"RM": 1}
    assert any("RM" in n for n in quality_notes(td))


def test_thai_windows_encoding_and_synonym_file():
    herbs = pd.DataFrame({"รหัสตำรับ": ["NR001/1", "NR001/1"], "ชื่อสมุนไพร": ["ขิงแห้ง", "ดีปลี"]})
    syn = pd.DataFrame({"ชื่อพ้อง": ["ขิงแห้ง"], "ชื่อหลัก": ["ขิง"]})
    td = read_files([("nr.csv", csv(herbs, "cp874")), ("ชื่อพ้อง.csv", csv(syn))])
    assert set(td.herbs["herb"]) == {"ขิง", "ดีปลี"}


def test_unrelated_csv_skipped():
    td = read_files([("notes.csv", csv(pd.DataFrame({"a": [1]})))])
    assert td.files[0].kind == "skipped"


def test_examples_import_cleanly_into_app_model():
    td = read_folder("data/examples")
    assert {f.kind for f in td.files} == {"herbs", "symptoms"}
    ref = pd.read_csv("data/reference/herb_reference.csv", dtype=str, keep_default_na=False)
    syn = pd.read_csv("data/reference/herb_synonyms.csv", dtype=str, keep_default_na=False)
    tables = to_app_tables(td, ref, syn)
    assert set(tables["prescriptions"]["scripture_id"]) == {"WRO", "NR", "WP"}
    assert "ขิงแห้ง" not in set(tables["herbs"]["herb_id"])  # synonyms merged
    rep = prepare(tables)
    assert rep.can_publish and not rep.warnings
