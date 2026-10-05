"""Generate a SAMPLE dataset so the app runs before the real data is ready.

The recipes are synthetic. Herb names, scientific names and the classic
formulas (ตรีกฏุก, ตรีผลา) are real, but which recipe contains what is random,
with a few pairs planted on purpose so the statistics pages have something
to find. Replace data/*.csv with the cleaned real dataset (see README).

    python -m preprocessing.make_sample_data
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SCRIPTURES = [
    ("WRO", "คัมภีร์จารึกวัดราชโอรสาราม", "Wat Ratchaorasaram inscriptions"),
    ("NR", "คัมภีร์โอสถพระนารายณ์", "Osot Phra Narai"),
    ("WP", "จารึกตำรายาวัดโพธิ์", "Wat Pho inscriptions"),
]

# herb_id (canonical Thai name), scientific name, safety level, safety note
HERBS = [
    ("ขิง", "Zingiber officinale Roscoe", "caution", "ระวังในผู้ที่ใช้ยาต้านการแข็งตัวของเลือด"),
    ("ดีปลี", "Piper retrofractum Vahl", "none", ""),
    ("พริกไทย", "Piper nigrum L.", "none", ""),
    ("มะกรูด", "Citrus hystrix DC.", "none", ""),
    ("ว่านน้ำ", "Acorus calamus L.", "caution", "มีสาร β-asarone ไม่ควรใช้ต่อเนื่องนาน"),
    ("กานพลู", "Syzygium aromaticum (L.) Merr. & L.M.Perry", "none", ""),
    ("ดอกจันทน์", "Myristica fragrans Houtt. (aril)", "caution", "ขนาดสูงทำให้เวียนศีรษะ ใจสั่น"),
    ("ลูกจันทน์", "Myristica fragrans Houtt. (seed)", "caution", "ขนาดสูงทำให้เวียนศีรษะ ใจสั่น"),
    ("กระวาน", "Amomum testaceum Ridl.", "none", ""),
    ("การบูร", "Cinnamomum camphora (L.) J.Presl", "caution", "ห้ามกินในปริมาณมาก เป็นพิษต่อระบบประสาท"),
    ("สมอไทย", "Terminalia chebula Retz.", "none", ""),
    ("สมอพิเภก", "Terminalia bellirica (Gaertn.) Roxb.", "none", ""),
    ("มะขามป้อม", "Phyllanthus emblica L.", "none", ""),
    ("ไพล", "Zingiber montanum (J.Koenig) Link ex A.Dietr.", "none", ""),
    ("กระเทียม", "Allium sativum L.", "caution", "ระวังในผู้ที่ใช้ยาต้านการแข็งตัวของเลือด"),
    ("ชะเอมเทศ", "Glycyrrhiza glabra L.", "caution", "ใช้นานอาจทำให้ความดันสูง โพแทสเซียมต่ำ"),
    ("เจตมูลเพลิงแดง", "Plumbago indica L.", "danger", "ระคายเคืองรุนแรง ห้ามใช้ในหญิงตั้งครรภ์"),
    ("แห้วหมู", "Cyperus rotundus L.", "none", ""),
    ("มหาหิงคุ์", "Ferula assa-foetida L.", "none", ""),
    ("เกลือสินเธาว์", "Sodium chloride (rock salt)", "none", ""),
    ("ไคร้เครือ", "Aristolochia pierrei Lecomte", "danger", "มีสาร aristolochic acid เป็นพิษต่อไตและก่อมะเร็ง ห้ามเตรียมใช้เอง"),
    ("บอระเพ็ด", "Tinospora crispa (L.) Hook.f. & Thomson", "caution", "ใช้ต่อเนื่องนานอาจเป็นพิษต่อตับ"),
    ("ฟ้าทะลายโจร", "Andrographis paniculata (Burm.f.) Nees", "caution", "ห้ามใช้ในหญิงตั้งครรภ์"),
    ("ขมิ้นชัน", "Curcuma longa L.", "none", ""),
    ("กะเพรา", "Ocimum tenuiflorum L.", "none", ""),
    ("ตะไคร้", "Cymbopogon citratus (DC.) Stapf", "none", ""),
    ("อบเชย", "Cinnamomum verum J.Presl", "none", ""),
    ("โกฐสอ", "Angelica dahurica (Hoffm.) Benth. & Hook.f. ex Franch. & Sav.", "none", ""),
    ("โกฐเขมา", "Atractylodes lancea (Thunb.) DC.", "none", ""),
    ("เทียนดำ", "Nigella sativa L.", "none", ""),
]

# Spellings found in the scriptures that mean the same herb
SYNONYMS = [
    ("ขิงแห้ง", "ขิง"),
    ("หว้านน้ำ", "ว่านน้ำ"),
    ("สมอไท", "สมอไทย"),
    ("พริกล่อน", "พริกไทย"),
    ("รากไคร้เครือ", "ไคร้เครือ"),
    ("เจตมูลเพลิง", "เจตมูลเพลิงแดง"),
    ("ผลมะขามป้อม", "มะขามป้อม"),
]

SYMPTOM_GROUPS = {
    "ไข้": ["ไข้", "ตัวร้อน", "หนาวสั่น", "ปวดศีรษะ", "กระหายน้ำ"],
    "ทางเดินหายใจ": ["ไอ", "มีเสมหะ", "เจ็บคอ", "แน่นหน้าอก"],
    "ทางเดินอาหาร": ["ท้องอืด", "จุกเสียด", "คลื่นไส้", "ท้องร่วง", "เบื่ออาหาร"],
    "ลม": ["เวียนหัว", "หน้ามืด", "อ่อนเพลีย"],
}

# Formulas planted per symptom group: (herbs, probability)
PLANTED = {
    "ไข้": [(["ขิง", "ดีปลี"], 0.55), (["บอระเพ็ด"], 0.35), (["ฟ้าทะลายโจร"], 0.25)],
    "ทางเดินหายใจ": [(["ขิง", "ดีปลี", "พริกไทย"], 0.45), (["ชะเอมเทศ"], 0.4), (["มะขามป้อม"], 0.25)],
    "ทางเดินอาหาร": [(["สมอไทย", "สมอพิเภก", "มะขามป้อม"], 0.4), (["กานพลู", "ดอกจันทน์"], 0.45), (["ขิง", "มะกรูด"], 0.3)],
    "ลม": [(["ว่านน้ำ", "ดีปลี"], 0.4), (["กระวาน", "ดอกจันทน์", "ลูกจันทน์"], 0.35), (["การบูร"], 0.3)],
}

NAME_PREFIX = {"ไข้": "แก้ไข้", "ทางเดินหายใจ": "แก้ไอ", "ทางเดินอาหาร": "แก้ท้องอืด", "ลม": "แก้ลม"}
FORMS = ["ยาผง", "ยาลูกกลอน", "ยาต้ม", "ยาดอง"]


def generate(seed: int = 7, n_recipes: int = 180) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed)
    herb_ids = [h[0] for h in HERBS]
    reverse_syn: dict[str, list[str]] = {}
    for syn, canon in SYNONYMS:
        reverse_syn.setdefault(canon, []).append(syn)

    prescriptions, ingredients, symptoms = [], [], []
    counters = {s[0]: 0 for s in SCRIPTURES}
    for _ in range(n_recipes):
        book = rng.choices([s[0] for s in SCRIPTURES], weights=[0.35, 0.45, 0.2])[0]
        counters[book] += 1
        rid = f"{book}{counters[book]:03d}/{rng.randint(1, 3)}"
        group = rng.choice(list(SYMPTOM_GROUPS))
        syms = rng.sample(SYMPTOM_GROUPS[group], k=rng.randint(1, 3))
        if rng.random() < 0.2:  # some recipes treat a second group too
            other = rng.choice([g for g in SYMPTOM_GROUPS if g != group])
            syms.append(rng.choice(SYMPTOM_GROUPS[other]))

        herbs: list[str] = []
        for formula, p in PLANTED[group]:
            if rng.random() < p:
                herbs += formula
        while len(set(herbs)) < rng.randint(3, 8):
            herbs.append(rng.choice(herb_ids))
        herbs = list(dict.fromkeys(herbs))
        if rng.random() < 0.05:
            herbs.append("ไคร้เครือ")

        prescriptions.append({
            "recipe_id": rid,
            "scripture_id": book,
            "name_th": f"{NAME_PREFIX[group]}{syms[0] if syms[0] != group else ''}".strip(),
            "form": rng.choice(FORMS),
            "original_text": "[ตัวอย่าง] ข้อความต้นฉบับจากคัมภีร์ ยังไม่ได้นำเข้า",
            "page_ref": f"หน้า {rng.randint(1, 240)}",
        })
        for h in herbs:
            raw = h
            if h in reverse_syn and rng.random() < 0.3:
                raw = rng.choice(reverse_syn[h])
            ingredients.append({"recipe_id": rid, "herb_raw": raw, "amount": f"{rng.randint(1, 8)} ส่วน"})
        for s in dict.fromkeys(syms):
            symptoms.append({"recipe_id": rid, "symptom": s})

    # recipe ids must be unique
    pres = pd.DataFrame(prescriptions).drop_duplicates("recipe_id")
    keep = set(pres["recipe_id"])
    ing = pd.DataFrame(ingredients)
    ing = ing[ing["recipe_id"].isin(keep)].drop_duplicates(["recipe_id", "herb_raw"])
    sym = pd.DataFrame(symptoms)
    sym = sym[sym["recipe_id"].isin(keep)].drop_duplicates()

    sym_rows = [{"symptom": s, "symptom_group": g} for g, ss in SYMPTOM_GROUPS.items() for s in ss]
    return {
        "scriptures": pd.DataFrame(SCRIPTURES, columns=["scripture_id", "name_th", "name_en"]),
        "prescriptions": pres,
        "ingredients": ing,
        "symptoms": sym,
        "symptom_groups": pd.DataFrame(sym_rows),
        "herbs": pd.DataFrame(HERBS, columns=["herb_id", "sci_name", "safety_level", "safety_note"]),
        "herb_synonyms": pd.DataFrame(SYNONYMS, columns=["synonym", "herb_id"]),
    }


EXAMPLE_DIR = DATA_DIR / "examples"


def write_team_csvs(tables: dict[str, pd.DataFrame], out: Path = EXAMPLE_DIR) -> None:
    """The same data in the team's format: per scripture, 1 herb file + 1 symptom file."""
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.csv"):
        old.unlink()
    herbs = tables["herbs"].set_index("herb_id")["sci_name"]
    ing = tables["ingredients"].merge(tables["prescriptions"][["recipe_id", "scripture_id", "name_th"]], on="recipe_id")
    sym = tables["symptoms"].merge(tables["prescriptions"][["recipe_id", "scripture_id"]], on="recipe_id")
    for book in tables["scriptures"]["scripture_id"]:
        h = ing[ing["scripture_id"] == book]
        pd.DataFrame({
            "รหัสตำรับ": h["recipe_id"],
            "ชื่อตำรับ": h["name_th"],
            "ชื่อสมุนไพร": h["herb_raw"],
            "ชื่อวิทยาศาสตร์": h["herb_raw"].map(herbs).fillna(""),
            "ปริมาณ": h["amount"],
        }).to_csv(out / f"{book}_herbs.csv", index=False, encoding="utf-8-sig")
        s = sym[sym["scripture_id"] == book]
        pd.DataFrame({"รหัสตำรับ": s["recipe_id"], "อาการ": s["symptom"]}).to_csv(
            out / f"{book}_symptoms.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    from preprocessing.import_team_csvs import build
    from core.team_csv import read_folder
    from preprocessing.prepare_data import publish

    tables = generate()
    write_team_csvs(tables)
    rep, _ = build(read_folder(EXAMPLE_DIR))
    for name in ("prescriptions",):  # keep the sample's extra columns (form, original text)
        rep.tables[name] = rep.tables[name].drop(columns=["form", "original_text", "page_ref"]).merge(
            tables[name][["recipe_id", "form", "original_text", "page_ref"]], on="recipe_id", how="left").fillna("")
    for old in DATA_DIR.glob("*.csv"):
        old.unlink()
    (DATA_DIR / "dataset.json").unlink(missing_ok=True)
    publish(rep, "0.1-sample", "ข้อมูลตัวอย่าง (สังเคราะห์)", is_sample=True)
    print(f"wrote 6 example CSVs to {EXAMPLE_DIR} and imported them into {DATA_DIR}")


if __name__ == "__main__":
    main()
