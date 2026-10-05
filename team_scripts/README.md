# Team scripts (6-CSV layout)

Put these 6 files in one folder (3 คัมภีร์ × 2 files):

| File | Columns | 1 row = |
| --- | --- | --- |
| `WRO_herbs.csv`, `NR_herbs.csv`, `RM_herbs.csv` | รหัสตำรับ, ชื่อสมุนไพร, ชื่อวิทยาศาสตร์ (optional) | 1 recipe × 1 herb |
| `WRO_symptoms.csv`, `NR_symptoms.csv`, `RM_symptoms.csv` | รหัสตำรับ, อาการ | 1 recipe × 1 symptom |

Old column names (รหัสตำรับยา, ชื่อสมุนไพรตามคัมภีร์, อาการต่างๆ, สรรพคุณ …) are renamed automatically.
Several symptoms in one cell separated by `,` `;` `/` are split. Optional `herb_synonyms.csv`
(ชื่อพ้อง, ชื่อหลัก) merges names like ขิงแห้ง → ขิง. To add a 4th คัมภีร์, edit `SCRIPTURES` in `remedy_data.py`.

```bash
pip install -r requirements.txt
python Application_search_remedy.py path/to/csv_folder   # search by symptom / recipe id
python Database.py path/to/csv_folder                    # Apriori + ขิงแห้ง/ดีปลี chart
```
