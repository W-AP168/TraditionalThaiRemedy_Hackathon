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

The repo ships with a **synthetic sample dataset** (`data/`, 180 recipes) so the app runs today.
Every page shows a banner while it is in use. The numbers are not results from the real scriptures.

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
  data_loader.py        load CSVs, apply synonym dictionary → Dataset
  search.py             symptom search + match score, herb lookups
  apriori.py            binary matrix, Apriori, association rules, herb pairs
  statistics.py         permutation test, Benjamini–Hochberg FDR, interpretation text
  network.py            knowledge graph (networkx + plotly)
  safety.py             safety flags per herb / recipe
  cache.py              disk cache keyed by (dataset fingerprint, parameters)
preprocessing/
  prepare_data.py       Excel → validate → normalize → synonyms → checks → publish version
  make_sample_data.py   regenerates the synthetic sample
tests/                  unit tests + every page renders
```

Analysis is cached: Apriori and permutation tests rerun only when the data or the settings change.

## Putting in the real data

Fill an Excel file with one sheet per table (same columns as the CSVs), then either upload it on
**จัดการข้อมูล**, or run:

```bash
python -m preprocessing.prepare_data cleaned.xlsx --version 1.0 --note "WRO + NR + RM"
```

| Sheet / file | Columns (required in **bold**) |
| --- | --- |
| prescriptions | **recipe_id**, **scripture_id**, **name_th**, form, original_text, page_ref |
| ingredients | **recipe_id**, **herb_raw**, amount |
| symptoms | **recipe_id**, **symptom** |
| herbs | **herb_id**, **sci_name**, safety_level (`none`/`caution`/`danger`), safety_note |
| herb_synonyms | **synonym**, **herb_id** |
| scriptures | **scripture_id**, **name_th**, name_en |
| symptom_groups | symptom, symptom_group |

Rules: one row = one herb (or one symptom) of one recipe · no merged cells · every row has a recipe_id.
Duplicate recipe ids block publishing; empty names and unmapped herbs are warnings.
Publishing archives the old version in `data/versions/<version>/`.

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
