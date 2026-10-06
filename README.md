# ThaiRx-AI

Explainable AI platform that **analyzes**, **recommends** and **discovers** Thai traditional medicine formulas,
for practitioners, researchers and students. Built from concept paper **ThaiRx-AI ฉบับปรับปรุงครั้งที่ 4 (6 ต.ค. 2569)**.
Not a prescribing tool and not treatment advice for the public.

Sources: `WRO` ศิลาจารึกวัดราชโอรสาราม · `NR` คัมภีร์โอสถพระนารายณ์ · `RM` ตำรับยาโรงพระโอสถ รัชกาลที่ 2

```bash
pip install -r requirements.txt
streamlit run app.py
```

The repo ships with a **sample (จำลอง) dataset** built from `data/examples/` (`python -m tools.make_sample_data`).
While it is loaded, every page shows a **จำลอง** badge. Real data shows **คำนวณจริง**.

## Pages

| Page | What it does |
| --- | --- |
| คัดเลือกตำรับ (Recommend) | symptoms/indications → readiness gate on **every** herb (Identity × Availability) → **ผ่านเกณฑ์เพื่อพัฒนา** vs **ตรงโจทย์แต่ยังมีข้อจำกัด** with limiting herbs. Industry / Research mode |
| วิเคราะห์ตำรับ (Analyze) | 3 separate sections: text as written · patterns from the database (rules, similar recipes by Jaccard, compare 2) · verified modern evidence |
| สร้างสมมติฐาน (Discover) | candidate herb set from high-lift, well-supported rules, with grades, safety, source recipes. Fixed label: สมมติฐานเพื่อการวิจัย — ต้องประเมินโดยผู้เชี่ยวชาญ |
| Back-end 🔒 | import + review queue (herb names, synonyms, คณาเภสัช, symptom mapping, duplicates, safety), grade editor, rules + network + permutation test, evaluation dashboard |

## Rules that the code enforces

- **Gate:** no averaging. One failing or ungraded herb fails the recipe; an unresolved name = ข้อมูลไม่พอ. Relevance never moves a recipe between groups (tested with 3 fixtures in `eval/gate_fixtures.py`).
- **Names:** synonyms and คณาเภสัช apply only when `review_status = verified`. Never auto-merged.
- **Rules:** typed items `HERB:` `SYMPTOM:` `INDICATION:`; duplicates (`duplicate_of`) excluded by default; every view shows support, confidence, lift, real recipe count, thresholds, denominator, books, data version; < 5 recipes = ข้อมูลน้อย.
- **Search:** exact term match (no "ตา" inside "ปวดตามข้อ").
- **Missing input → "ข้อมูลไม่พอ"**, never a guess.

## Code

```
app.py                      navigation
prepare_data.py             import team files → data/ (CLI)
pages/                      0_Home, 1_Recommend, 2_Analyze, 3_Discover, 9_Backend
backend/                    back-end tabs (data, grades, rules, evaluation)
core/data.py                data model (spec §4), loading, คณาเภสัช expansion, synonym resolution, versioning
core/ingest.py              team CSV/Excel → tables (recognised by columns), checks, publish
core/rules.py               Apriori engine (mlxtend), 3 analysis types, metadata, cache
core/gate.py                readiness gate     core/recommend.py   match → gate → 2 groups
core/scoring.py             relevance score, keyword baseline, Precision@k
core/similarity.py          Jaccard            core/statistics.py  permutation test, FDR
eval/                       gate fixtures, Precision@5 harness
team_scripts/               the team's scripts, now on the shared reader
tests/                      pytest
```

## Loading the real data

Files can have any name; each CSV / Excel sheet is recognised by its columns
(รหัสตำรับ + ชื่อสมุนไพร → herbs, + อาการ → symptoms, + ข้อบ่งใช้ → indications, + สรรพคุณ/ข้อความต้นฉบับ/วิธีทำ/กระสายยา → recipe info;
reference tables: herb list, ชื่อพ้อง, คณาเภสัช, grades (identity/availability), คำเตือน). Excel is read with calamine.

- Website: Back-end → ข้อมูล & ตรวจสอบ → upload → read the checks → เผยแพร่
- CLI: `python prepare_data.py data/raw` (check) then `python prepare_data.py data/raw --version 0.2`

`data/reference/` holds the only defaults shipped: ตรีกฏุก and โกฐทั้ง 5 members and the ไคร้เครือ warning, all taken
from the concept paper. Sample grades are never carried into real data.

### Inputs still needed from the team (spec §11)
Herb grading table · INDICATION column · reviewed synonym table · คณาเภสัช member lists (ตรีผลา …) · duplicate flags ·
RM herbs/symptoms in long format · expert test queries + relevance labels (`data/eval_queries.csv`, `data/eval_labels.csv`) ·
relevance weights (defaults 1.0 symptom / 0.5 indication, editable in Back-end).

## Deploy (Streamlit Community Cloud)
share.streamlit.io → repo, branch, `app.py` → Secrets: `lab_password = "..."` → Deploy.
Data published on the website is lost on restart: download the zip in Back-end and commit `data/`.

## Tests
`python -m pytest`
