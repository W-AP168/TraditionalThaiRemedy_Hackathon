# Team scripts (WRO, NR, WP)

Put the cleaned CSVs in one folder. **File names don't matter**: each file is recognised by its columns
(รหัสตำรับ + ชื่อสมุนไพร = herb file, รหัสตำรับ + อาการ/สรรพคุณ = symptom file, both = old combined file).
The scripture comes from the recipe id; RM rows are skipped. Optional synonym file: put "synonym" or
"ชื่อพ้อง" in its name (columns: ชื่อพ้อง, ชื่อหลัก).

The reader is shared with the website (`core/team_csv.py`), so both always read the data the same way.

```bash
pip install -r requirements.txt
python Application_search_remedy.py path/to/csv_folder   # search by symptom / recipe id
python Database.py path/to/csv_folder                    # Apriori + ขิง/ดีปลี chart
```
Try it now with the example files: `python Database.py ../data/examples`
