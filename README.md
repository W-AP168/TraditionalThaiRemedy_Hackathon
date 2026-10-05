# ตำรับยาไทย — Thai Traditional Medicine Knowledge System

From ancient scriptures to data evidence:

```
Ancient scriptures → Data pipeline → Public knowledge (search, recipes, safety)
                                   → Research Lab (Apriori, permutation tests) → Knowledge graph
```

UI design: [Thai Remedy Miner UI Draft](https://claude.ai/artifact/8MK6Y2aqGGNahiEhtnGH4k), page "v2 · ตำรับยาไทย".

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The repo ships with a **synthetic sample dataset** (`data/`, 180 recipes, built from `data/examples/` by `python -m preprocessing.make_sample_data`) so the app runs today.
Every page shows a banner while it is in use. The numbers are not results from the real scriptures.

## Put it online (Streamlit Community Cloud, free)

1. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, click **Create app**.
2. Repo `W-AP168/TraditionalThaiRemedy_Hackathon`, branch `main` (or this PR's branch), main file `app.py`.
3. **Advanced settings → Secrets**: `lab_password = "..."` (protects the Research Lab and data upload).
4. **Deploy** → you get a public `….streamlit.app` link.

Data published on the website is lost when the cloud app restarts. To keep it: จัดการข้อมูล →
**ดาวน์โหลดชุดข้อมูล (.zip)** → unzip over `data/` → commit to GitHub (the app redeploys itself).
The app sleeps after a few days without visitors; open the link a few minutes before a demo.

## Pages

| Explore (public) | Research Lab 🔬 |
| --- | --- |
| หน้าแรก: hero, two search cards | Research Dashboard: counts, knowledge network, top pairs |
| สำรวจตำรับ: browse/search all recipes | Apriori Lab: support / confidence / lift sliders, rules table, CSV |
| ค้นหาอาการ: symptom search, match score | หลักฐานทางสถิติ: observed vs random lift, permutation histogram, p, FDR q |
| รายละเอียดตำรับ: herbs, safety warning, original text, herb pairs | Knowledge Graph: pick a herb, see partners, "Why this herb?" |
| คลังสมุนไพร: herb profile + pairs | จัดการข้อมูล: upload Excel, validation report, publish new version |

Optional password for the Research Lab: create `.streamlit/secrets.toml` with `lab_password = "..."`.

## Code layout

```
app.py                  navigation (Explore / Research Lab)
ui.py                   theme, cached data access, shared UI pieces
pages/                  one file per page
core/
  team_csv.py           read the team's CSVs (detect by columns, WRO/NR/WP) → app tables
  data_loader.py        load CSVs, apply synonym dictionary → Dataset
  search.py             symptom search + match score, herb lookups
  apriori.py            binary matrix, Apriori, association rules, herb pairs
  statistics.py         permutation test, Benjamini–Hochberg FDR, interpretation text
  network.py            knowledge graph (networkx + plotly)
  safety.py             safety flags per herb / recipe
  cache.py              disk cache keyed by (dataset fingerprint, parameters)
preprocessing/
  import_team_csvs.py   team CSVs → checks → publish (CLI)
  prepare_data.py       Excel → validate → normalize → synonyms → checks → publish version
  make_sample_data.py   regenerates the synthetic sample
tests/                  unit tests + every page renders
```

Analysis is cached: Apriori and permutation tests rerun only when the data or the settings change.

## Putting in the real data (WRO, NR, WP)

File names don't matter. Each CSV is recognised by its **columns**:

| File has | Treated as | 1 row = |
| --- | --- | --- |
| รหัสตำรับ + ชื่อสมุนไพร (+ ชื่อวิทยาศาสตร์, ปริมาณ, ชื่อตำรับ) | herb file | 1 recipe × 1 herb |
| รหัสตำรับ + อาการ (or อาการต่างๆ / สรรพคุณ) | symptom file | 1 recipe × 1 symptom |
| both (old `clean_database_*.csv`) | both | |
| "synonym" or "ชื่อพ้อง" in the file name | synonym list (ชื่อพ้อง, ชื่อหลัก) | |

- The scripture comes from the recipe id (`WRO133/1` → WRO). Rows of other scriptures (e.g. RM) are skipped and reported.
- Old column names (รหัสตำรับยา, ชื่อสมุนไพรตามคัมภีร์, ชื่อข้อมูลยา, ชื่อทยาศาสตร์ …), Thai Windows encoding,
  merged cells, extra spaces and "ไข้, ไอ" in one cell are all handled.
- Example of the expected layout: `data/examples/` (6 files).

Two ways to load:

1. Website: Research Lab → **จัดการข้อมูล** → upload the CSVs (or put them in `data/raw/` and click
   "ตรวจไฟล์ในโฟลเดอร์ data/raw") → read the check report → **Publish**.
2. Command line: put the CSVs in `data/raw/`, then
   ```bash
   python -m preprocessing.import_team_csvs                 # check only
   python -m preprocessing.import_team_csvs --version 0.2   # check + publish
   ```

Safety notes and missing scientific names come from `data/reference/herb_reference.csv`; shared synonyms from
`data/reference/herb_synonyms.csv`. **Both reference files were drafted for the demo and must be checked
by the team.** To change the scriptures, edit `SCRIPTURE_NAMES` in `core/team_csv.py`.

Publishing archives the old version in `data/versions/<version>/` and clears the analysis cache.

## The statistics, in one paragraph

Each recipe becomes a row of 0/1 (herb absent/present). Apriori finds herb sets that appear together often.
For a pair A, B: **lift** = how many times more often they co-occur than if independent.
To check that this isn't chance, herb B's column is shuffled across recipes 1,000 times (keeps how often each herb
is used, breaks any link). p = share of shuffles reaching the observed lift. q-values correct for testing many pairs (FDR).

What we claim: *statistically enriched associations observed in historical prescriptions*. These may reflect recurring
formulation patterns. They are **not** proof of clinical efficacy or causality.

## Tests

```bash
python -m pytest
```
