import io

import pandas as pd
import pytest

from core.data import SCHEMA, load, resolve_items
from core.ingest import build_tables, publish, read_sources


def csv(df: pd.DataFrame, enc: str = "utf-8-sig") -> bytes:
    return df.to_csv(index=False).encode(enc)


def empty_ref():
    return {n: pd.DataFrame(columns=SCHEMA[n]) for n in ("herbs", "herb_synonyms", "herb_groups", "herb_grades",
                                                       "herb_safety", "evidence")}


def team_files():
    recipes = pd.DataFrame({"รหัสตำรับยา": ["WRO001/1", "NR002/1", "RM003/1"],
                            "สรรพคุณ": ["แก้ไข้ ตัวร้อน", "แก้ไอ", "แก้ลม"],
                            "กระสายยา": ["น้ำผึ้ง", "", ""]})
    herbs = pd.DataFrame({"รหัสตำรับ": ["WRO001/1", "", "NR002/1", "WP009/1"],   # blank = merged cell
                          "ชื่อสมุนไพรตามคัมภีร์": [" ขิงแห้ง ", "ตรีกฏุก", "ดีปลี", "ขิง"],
                          "ปริมาณ": ["2 บาท", "1 บาท", "๔ สลึง", "1"]})
    symptoms = pd.DataFrame({"รหัสตำรับ": ["WRO001/1", "NR002/1"], "อาการ": ["ไข้, ตัวร้อน", "ไอ"]})
    return [("recipes_X.csv", csv(recipes)), ("whatever name.csv", csv(herbs)), ("sym.csv", csv(symptoms, "cp874"))]


def test_files_recognised_by_columns():
    imp = read_sources(team_files())
    kinds = {s.name: s.kinds for s in imp.sources}
    assert kinds["recipes_X.csv"] == ["recipes"]
    assert kinds["whatever name.csv"] == ["recipe_herbs"]
    assert kinds["sym.csv"] == ["recipe_symptoms"]
    assert imp.skipped_books == {"WP": 1}                     # WP no longer used
    t, checks = build_tables(imp, empty_ref())
    assert set(t["recipes"]["book"]) == {"WRO", "NR", "RM"}
    # สรรพคุณ is the indication text, NOT a symptom
    assert t["recipes"].set_index("recipe_id").at["WRO001/1", "indication_text"] == "แก้ไข้ ตัวร้อน"
    # merged cell filled down; "ไข้, ตัวร้อน" split
    assert set(t["recipe_herbs"].query("recipe_id == 'WRO001/1'")["herb_name_original"]) == {"ขิงแห้ง", "ตรีกฏุก"}
    assert set(t["recipe_symptoms"].query("recipe_id == 'WRO001/1'")["symptom_original"]) == {"ไข้", "ตัวร้อน"}
    # "2 บาท" → 2 + บาท ; Thai digits converted
    h = t["recipe_herbs"].set_index("herb_name_original")
    assert (h.at["ขิงแห้ง", "qty_original"], h.at["ขิงแห้ง", "unit_original"]) == ("2", "บาท")
    assert h.at["ดีปลี", "qty_original"] == "4"
    # % only when all herbs share a unit: WRO001/1 = 2+1 บาท
    assert h.at["ขิงแห้ง", "qty_percent"] == "66.7"
    assert any("RM" in c.detail and not c.ok for c in checks)  # RM not split warned


def test_excel_all_sheets_read():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame({"รหัสตำรับ": ["NR001/1"], "ชื่อสมุนไพร": ["ขิง"]}).to_excel(xw, sheet_name="NR_herbs", index=False)
        pd.DataFrame({"รหัสตำรับ": ["NR001/1"], "อาการ": ["ไอ"]}).to_excel(xw, sheet_name="NR_sym", index=False)
    imp = read_sources([("team.xlsx", buf.getvalue())])
    assert {k for s in imp.sources for k in s.kinds} == {"recipe_herbs", "recipe_symptoms"}


def kb_from(t_extra: dict, tmp_path):
    imp = read_sources(team_files())
    ref = empty_ref()
    ref.update(t_extra)
    t, _ = build_tables(imp, ref)
    publish(t, "t1", data_dir=tmp_path)
    return load(tmp_path)


def test_only_verified_groups_and_synonyms_resolve(tmp_path):
    herbs = pd.DataFrame([{"herb_id": h, "std_name_th": h, "review_status": "verified"}
                          for h in ("ขิง", "ดีปลี", "พริกไทย")])
    syn = pd.DataFrame([{"alias": "ขิงแห้ง", "herb_id": "ขิง", "review_status": "pending"}])
    grp = pd.DataFrame([{"group_name": "ตรีกฏุก", "herb_id": h, "review_status": "verified"}
                        for h in ("ขิง", "ดีปลี", "พริกไทย")])
    kb = kb_from({"herbs": herbs, "herb_synonyms": syn, "herb_groups": grp}, tmp_path)
    it = kb.herbs_of("WRO001/1")
    # pending synonym → not merged, herb_id empty (รอตรวจสอบ)
    khing = it[it["herb_name_original"] == "ขิงแห้ง"].iloc[0]
    assert khing["herb_id"] == "" and not khing["resolved"]
    # verified group expanded, traceable
    grp_rows = it[it["from_group"] == "ตรีกฏุก"]
    assert set(grp_rows["herb_id"]) == {"ขิง", "ดีปลี", "พริกไทย"}

    syn.loc[0, "review_status"] = "verified"
    kb.t["herb_synonyms"] = syn
    items = resolve_items(kb.t)
    assert set(items.query("recipe_id == 'WRO001/1'")["item"]) == {"ขิง", "ดีปลี", "พริกไทย"}  # merged, no dup


def test_missing_files_are_warnings_not_crashes(tmp_path):
    kb = load(tmp_path)
    assert kb.recipes.empty and kb.items.empty
    assert any("recipes" in w for w in kb.warnings)
