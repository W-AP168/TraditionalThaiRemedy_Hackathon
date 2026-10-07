"""Build the SAMPLE (จำลอง) dataset so the app runs before the real data is ready.

Herb names and scientific names are real. Everything else (which recipe has
what, grades, indications, duplicates) is synthetic, and the whole dataset is
flagged is_sample → every page shows a "จำลอง" badge.

The sample mirrors the real state of the data: WRO and NR split into herbs and
symptoms, RM not split yet, ตรีกฏุก written as one item in some recipes, some
synonyms still pending, grades incomplete.

It is written in the TEAM's file format (data/examples/) and imported through
the same path as real data:

    python -m tools.make_sample_data
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

from core.data import DATA_DIR, read_table
from core.ingest import build_tables, publish, read_sources

EXAMPLE_DIR = DATA_DIR / "examples"
REF_DIR = DATA_DIR / "reference"

HERBS = [  # std name, scientific name
    ("ขิง", "Zingiber officinale Roscoe"), ("ดีปลี", "Piper retrofractum Vahl"), ("พริกไทย", "Piper nigrum L."),
    ("มะกรูด", "Citrus hystrix DC."), ("ว่านน้ำ", "Acorus calamus L."),
    ("กานพลู", "Syzygium aromaticum (L.) Merr. & L.M.Perry"), ("ดอกจันทน์", "Myristica fragrans Houtt. (aril)"),
    ("ลูกจันทน์", "Myristica fragrans Houtt. (seed)"), ("กระวาน", "Amomum testaceum Ridl."),
    ("การบูร", "Cinnamomum camphora (L.) J.Presl"), ("สมอไทย", "Terminalia chebula Retz."),
    ("สมอพิเภก", "Terminalia bellirica (Gaertn.) Roxb."), ("มะขามป้อม", "Phyllanthus emblica L."),
    ("ไพล", "Zingiber montanum (J.Koenig) Link ex A.Dietr."), ("กระเทียม", "Allium sativum L."),
    ("ชะเอมเทศ", "Glycyrrhiza glabra L."), ("เจตมูลเพลิงแดง", "Plumbago indica L."),
    ("แห้วหมู", "Cyperus rotundus L."), ("ไคร้เครือ", "Aristolochia pierrei Lecomte"),
    ("บอระเพ็ด", "Tinospora crispa (L.) Hook.f. & Thomson"), ("ขมิ้นชัน", "Curcuma longa L."),
    ("ตะไคร้", "Cymbopogon citratus (DC.) Stapf"), ("อบเชย", "Cinnamomum verum J.Presl"),
    ("โกฐสอ", "Angelica dahurica (Hoffm.) Benth. & Hook.f. ex Franch. & Sav."),
    ("โกฐเขมา", "Atractylodes lancea (Thunb.) DC."), ("โกฐเชียง", "Angelica sinensis (Oliv.) Diels"),
    ("โกฐหัวบัว", "Ligusticum chuanxiong Hort."), ("โกฐจุฬาลัมพา", "Artemisia annua L."),
    ("เทียนดำ", "Nigella sativa L."), ("เถาวัลย์เปรียง", "Derris scandens (Roxb.) Benth."),
]
# alias, std name, status
SYNONYMS = [("ขิงแห้ง", "ขิง", "verified"), ("หว้านน้ำ", "ว่านน้ำ", "verified"), ("สมอไท", "สมอไทย", "verified"),
            ("รากไคร้เครือ", "ไคร้เครือ", "verified"), ("พริกล่อน", "พริกไทย", "pending")]
NOT_IN_MASTER = ["เถาวัลย์เปรียง"]          # stays unresolved → รอตรวจสอบ

GROUPS = {  # symptom group → symptoms, indication, planted formulas (herbs, prob)
    "ไข้": (["ไข้", "ตัวร้อน", "หนาวสั่น", "ปวดศีรษะ"], "ไข้",
            [(["ขิง", "ดีปลี"], .5), (["บอระเพ็ด"], .4)]),
    "หายใจ": (["ไอ", "มีเสมหะ", "เจ็บคอ", "แน่นหน้าอก"], "หืดไอ",
              [(["ตรีกฏุก"], .35), (["ขิง", "ดีปลี", "พริกไทย"], .25), (["ชะเอมเทศ"], .45), (["มะขามป้อม"], .3)]),
    "อาหาร": (["ท้องอืด", "จุกเสียด", "คลื่นไส้", "ท้องร่วง"], "ธาตุพิการ",
              [(["สมอไทย", "สมอพิเภก", "มะขามป้อม"], .4), (["กานพลู", "ดอกจันทน์"], .45), (["ขิง", "มะกรูด"], .3)]),
    "ลม": (["เวียนหัว", "หน้ามืด", "อ่อนเพลีย"], "ลมวิงเวียน",
           [(["ว่านน้ำ", "ดีปลี"], .4), (["กระวาน", "ดอกจันทน์", "ลูกจันทน์"], .35), (["โกฐทั้ง 5"], .3)]),
    "ปวด": (["ปวดข้อ", "ข้อบวม", "ปวดเมื่อย"], "ลมจับโปง",
            [(["ไพล", "ขมิ้นชัน"], .45), (["เถาวัลย์เปรียง"], .5), (["ขิง", "พริกไทย"], .3)]),
}
NAME = {"ไข้": "แก้ไข้", "หายใจ": "แก้ไอ", "อาหาร": "แก้ธาตุพิการ", "ลม": "แก้ลมวิงเวียน", "ปวด": "แก้ปวดข้อ"}
FORMS = ["ยาผง", "ยาลูกกลอน", "ยาต้ม"]
VEHICLES = ["น้ำผึ้ง", "น้ำร้อน", "น้ำมะนาว"]
UNITS = ["บาท", "สลึง", "ส่วน"]


def generate(seed: int = 11) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed)
    names = [h for h, _ in HERBS]
    sci = dict(HERBS)
    rev = {}
    for a, s, _ in SYNONYMS:
        rev.setdefault(s, []).append(a)

    recipes, herbs, symptoms, indications = [], [], [], []
    plan = {"WRO": 120, "NR": 85, "RM": 40}
    made = {}
    for book, n in plan.items():
        for i in range(1, n + 1):
            rid = f"{book}{i:03d}/{rng.randint(1, 3)}"
            g = rng.choice(list(GROUPS))
            syms, ind, planted = GROUPS[g]
            chosen = rng.sample(syms, k=rng.randint(1, 3))
            if rng.random() < .15:
                chosen.append(rng.choice(GROUPS[rng.choice(list(GROUPS))][0]))
            items = []
            for formula, p in planted:
                if rng.random() < p:
                    items += formula
            while len(set(items)) < rng.randint(3, 7):
                items.append(rng.choice(names))
            if rng.random() < .04:
                items.append("ไคร้เครือ")
            items = list(dict.fromkeys(items))
            unit = rng.choice(UNITS)
            made[rid] = (items, chosen, ind, unit)
            recipes.append({"รหัสตำรับ": rid, "ชื่อตำรับ": f"[จำลอง] ยา{NAME[g]}",
                            "ข้อความต้นฉบับ": "",  # not imported yet: shown as missing, never faked
                            "สรรพคุณ": "[จำลอง] " + " ".join(dict.fromkeys(chosen)),
                            "วิธีทำ": f"[จำลอง] ทำเป็น{rng.choice(FORMS)}", "กระสายยา": rng.choice(VEHICLES),
                            "รูปแบบยา": rng.choice(FORMS), "วิธีใช้": "[จำลอง]", "ซ้ำกับ": ""})
            if book == "RM":
                continue  # RM: herbs/symptoms not split yet (as in the real data)
            for h in items:
                raw = rng.choice(rev[h]) if h in rev and rng.random() < .3 else h
                herbs.append({"รหัสตำรับ": rid, "ชื่อสมุนไพร": raw, "ชื่อวิทยาศาสตร์": sci.get(h, ""),
                              "ปริมาณ": f"{rng.randint(1, 8)} {unit}"})
            for s in dict.fromkeys(chosen):
                symptoms.append({"รหัสตำรับ": rid, "อาการ": s})
            indications.append({"รหัสตำรับ": rid, "ข้อบ่งใช้": ind})

    # NR copies of WRO recipes (duplicates)
    rec = pd.DataFrame(recipes)
    wro = [r for r in made if r.startswith("WRO")][:6]
    nr = [r for r in made if r.startswith("NR")][-6:]
    for src, dst in zip(wro, nr):
        rec.loc[rec["รหัสตำรับ"] == dst, "ซ้ำกับ"] = src
        herbs = [h for h in herbs if h["รหัสตำรับ"] != dst] + [
            {**h, "รหัสตำรับ": dst} for h in herbs if h["รหัสตำรับ"] == src]

    grades_rng = random.Random(seed + 1)
    grades = []
    for h, _ in HERBS:
        if h in NOT_IN_MASTER or grades_rng.random() < .08:  # some herbs not graded yet
            continue
        grades.append({"herb_id": h,
                       "identity": grades_rng.choices("ABCD", [.7, .24, .05, .01])[0],
                       "availability": grades_rng.choices("ABCDE", [.8, .1, .06, .03, .01])[0],
                       "source": "[จำลอง] ข้อมูลทดสอบระบบ", "reason": "[จำลอง]", "assessor": "[จำลอง]",
                       "assessed_date": "2026-10-06"})
    return {
        "recipes": rec,
        "herbs": pd.DataFrame(herbs),
        "symptoms": pd.DataFrame(symptoms),
        "indications": pd.DataFrame(indications),
        "herb_master": pd.DataFrame([{"herb_id": h, "std_name_th": h, "sci_name": s, "review_status": "verified"}
                                     for h, s in HERBS if h not in NOT_IN_MASTER]),
        "synonyms": pd.DataFrame([{"alias": a, "herb_id": s, "review_status": st,
                                   "reviewed_by": "[จำลอง]" if st == "verified" else ""} for a, s, st in SYNONYMS]),
        "grades": pd.DataFrame(grades),
    }


def write_examples(t: dict[str, pd.DataFrame], out: Path = EXAMPLE_DIR) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.csv"):
        old.unlink()
    paths = []
    for book in ("WRO", "NR", "RM"):
        for name, df in (("recipes", t["recipes"]), ("herbs", t["herbs"]), ("symptoms", t["symptoms"]),
                         ("indications", t["indications"])):
            part = df[df["รหัสตำรับ"].str.startswith(book)]
            if part.empty:
                continue
            p = out / f"{name}_{book}.csv"
            part.to_csv(p, index=False, encoding="utf-8-sig")
            paths.append(p)
    for name in ("herb_master", "synonyms", "grades"):
        p = out / f"{name}.csv"
        t[name].to_csv(p, index=False, encoding="utf-8-sig")
        paths.append(p)
    return paths


def main() -> None:
    paths = write_examples(generate())
    imp = read_sources([(p.name, p) for p in paths])
    ref = {n: read_table(n, REF_DIR)[0] for n in ("herb_groups", "herb_safety")}
    tables, _ = build_tables(imp, ref)
    for old in DATA_DIR.glob("*.csv"):
        old.unlink()
    (DATA_DIR / "dataset.json").unlink(missing_ok=True)
    publish(tables, "0.1-sample", "ข้อมูลจำลอง", is_sample=True)
    print(f"sample: {len(tables['recipes'])} recipes from {len(paths)} example files → {DATA_DIR}")


if __name__ == "__main__":
    main()
