# Team scripts (WRO, NR, RM)

`Application_search_remedy.py` (search) and `Database.py` (Apriori + ขิง/ดีปลี chart) now read files with the same
reader as the website (`core/ingest.py`): any file names, recognised by columns, Excel via calamine,
synonyms/คณาเภสัช only when verified.

```bash
pip install -r ../requirements.txt
python Database.py ../data/examples
python Application_search_remedy.py ../data/examples
```
