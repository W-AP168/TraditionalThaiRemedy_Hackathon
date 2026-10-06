"""Knowledge base: the tables of spec section 4, loaded from data/*.csv.

Rules kept here:
- A missing table is an empty table plus a warning, never a crash.
- Original text and normalized value sit side by side.
- คณาเภสัช are expanded and aliases are resolved ONLY from reviewed rows
  (review_status == "verified"). Anything else keeps herb_id = "" and shows
  as "รอตรวจสอบ".
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

BOOKS = {
    "WRO": "ศิลาจารึกวัดราชโอรสาราม",
    "NR": "คัมภีร์โอสถพระนารายณ์",
    "RM": "ตำรับยาโรงพระโอสถ รัชกาลที่ 2",
}

SCHEMA: dict[str, list[str]] = {
    "recipes": ["recipe_id", "book", "name", "original_text", "indication_text", "preparation", "vehicle",
                "dosage_form", "usage", "category", "duplicate_of", "review_status"],
    "recipe_herbs": ["recipe_id", "herb_name_original", "herb_id", "part_used", "qty_original", "unit_original",
                     "qty_percent", "qty_rule", "from_group"],
    "herbs": ["herb_id", "std_name_th", "sci_name", "review_status", "taste", "pikat"],
    "herb_synonyms": ["alias", "herb_id", "reviewed_by", "review_status"],
    "herb_groups": ["group_name", "herb_id", "reviewed_by", "review_status"],
    "recipe_symptoms": ["recipe_id", "symptom_original", "symptom_modern", "mapping_reason", "mapped_by"],
    "recipe_indications": ["recipe_id", "indication"],
    "herb_grades": ["herb_id", "identity", "availability", "source", "reason", "assessor", "assessed_date",
                    "supply_area", "season", "volume_note"],
    "herb_safety": ["herb_id", "warning_text", "source"],
    "evidence": ["evidence_id", "herb_id", "recipe_id", "finding", "direction", "study_type", "pmid", "doi",
                 "title", "year", "quote", "reviewer", "review_status"],
    "review_log": ["timestamp", "reviewer", "action", "table", "detail", "data_version"],
}
# tables the app cannot do anything useful without
CORE_TABLES = ("recipes", "recipe_herbs")

IDENTITY_GRADES = {
    "A": "ชนิดเดียวชัดเจน / แหล่งที่มาเดียวชัดเจน",
    "B": "มีมากกว่า 1 ชนิดที่ยอมรับ ใช้แทนกันได้ ยังไม่ชัดว่าชนิดไหนดีกว่า",
    "C": "ชนิดหรือแหล่งที่มายังถกเถียงกันมาก",
    "D": "ไม่ทราบว่าคืออะไร หรือมาจากไหน",
}
AVAILABILITY_GRADES = {
    "A": "วัตถุดิบถูกต้อง มีขายสม่ำเสมอ พร้อมระดับอุตสาหกรรม",
    "B": "มีขายในตลาด แต่ไม่แน่ใจความถูกต้องของวัตถุดิบ",
    "C": "มีเฉพาะบางตลาด/ฤดู/พื้นที่ อาจต้องสั่ง",
    "D": "เก็บจากป่า หายาก เข้าถึงยาก",
    "E": "ไม่มีแหล่งเลย",
}
REVIEW_LABEL = {"verified": "ยืนยันแล้ว", "pending": "รอตรวจสอบ", "rejected": "ไม่ผ่าน"}
PENDING = "รอตรวจสอบ"


def clean(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = " ".join(str(value).split())
    return "" if text.lower() in {"nan", "none", "null", "-"} else text


def read_table(name: str, data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, bool]:
    """(table, existed). Missing columns are added empty."""
    path = Path(data_dir) / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame(columns=SCHEMA[name]), False
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for col in SCHEMA[name]:
        if col not in df.columns:
            df[col] = ""
    for col in df.columns:
        df[col] = df[col].map(clean)
    return df, True


def fingerprint(data_dir: Path = DATA_DIR) -> str:
    h = hashlib.sha256()
    for p in sorted(Path(data_dir).glob("*.csv")):
        if p.name == "review_log.csv":
            continue
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def verified(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["review_status"] == "verified"]


@dataclass
class KB:
    t: dict[str, pd.DataFrame]
    meta: dict
    warnings: list[str] = field(default_factory=list)
    fingerprint: str = ""
    items: pd.DataFrame = field(default_factory=pd.DataFrame)   # resolved recipe herbs

    # ---------- basics ----------
    @property
    def recipes(self) -> pd.DataFrame:
        return self.t["recipes"]

    @property
    def is_sample(self) -> bool:
        return bool(self.meta.get("is_sample"))

    @property
    def version(self) -> str:
        v = self.meta.get("version", "0")
        edits = (self.t["review_log"]["data_version"].str.split("+").str[0] == v).sum()
        return f"{v}+r{edits}" if edits else v

    def recipe(self, recipe_id: str) -> pd.Series:
        return self.recipes.set_index("recipe_id").loc[recipe_id]

    def herb_name(self, herb_id: str) -> str:
        if not herb_id:
            return ""
        h = self.t["herbs"].set_index("herb_id")
        return h.at[herb_id, "std_name_th"] or herb_id if herb_id in h.index else herb_id

    # ---------- per recipe ----------
    def herbs_of(self, recipe_id: str) -> pd.DataFrame:
        return self.items[self.items["recipe_id"] == recipe_id]

    def symptoms_of(self, recipe_id: str) -> pd.DataFrame:
        s = self.t["recipe_symptoms"]
        return s[s["recipe_id"] == recipe_id]

    def indications_of(self, recipe_id: str) -> list[str]:
        i = self.t["recipe_indications"]
        return i.loc[i["recipe_id"] == recipe_id, "indication"].tolist()

    def herb_set(self, recipe_id: str) -> set[str]:
        return set(self.herbs_of(recipe_id)["item"])

    # ---------- per herb ----------
    def grade(self, herb_id: str) -> dict:
        g = self.t["herb_grades"]
        row = g[g["herb_id"] == herb_id]
        return row.iloc[0].to_dict() if not row.empty else {}

    def safety(self, herb_id: str) -> list[dict]:
        s = self.t["herb_safety"]
        return s[s["herb_id"] == herb_id].to_dict("records")

    # ---------- vocabularies ----------
    def symptom_terms(self) -> list[str]:
        s = self.t["recipe_symptoms"]
        terms = pd.concat([s["symptom_original"], s["symptom_modern"]])
        return sorted({x for x in terms if x})

    def indication_terms(self) -> list[str]:
        return sorted({x for x in self.t["recipe_indications"]["indication"] if x})

    def pending_counts(self) -> dict[str, int]:
        it = self.items
        syn = self.t["herb_synonyms"]
        return {
            "ชื่อสมุนไพรที่ยังไม่ยืนยัน": int(it.loc[~it["resolved"], "herb_name_original"].nunique()),
            "ชื่อพ้องรอตรวจสอบ": int((syn["review_status"] != "verified").sum()),
            "อาการที่ยังไม่ได้เทียบคำสมัยใหม่": int((self.t["recipe_symptoms"]["symptom_modern"] == "").sum()),
            "ตำรับรอตรวจสอบ": int((self.recipes["review_status"] != "verified").sum()),
            "สมุนไพรที่ยังไม่มีเกรด": int(len(set(it.loc[it["resolved"], "herb_id"])
                                             - set(self.t["herb_grades"]["herb_id"]))),
        }


def resolve_items(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Expand verified คณาเภสัช, then map names to herb_id via herbs + verified synonyms.

    Output, one row per (recipe, herb after expansion):
      recipe_id, herb_name_original, herb_id ("" = unresolved), resolved, item
      (herb_id, or the original name when unresolved), from_group, part_used,
      qty_original, unit_original, qty_percent, qty_rule
    """
    herbs = t["herbs"]
    by_id = {h: h for h in herbs["herb_id"] if h}
    by_name = {n: h for n, h in zip(herbs["std_name_th"], herbs["herb_id"]) if n and h}
    syn = verified(t["herb_synonyms"])
    by_alias = {a: h for a, h in zip(syn["alias"], syn["herb_id"]) if a and h}
    groups = verified(t["herb_groups"]).groupby("group_name")["herb_id"].apply(list).to_dict()

    def resolve(name: str) -> str:
        return by_id.get(name) or by_name.get(name) or by_alias.get(name) or ""

    rows = []
    for r in t["recipe_herbs"].to_dict("records"):
        name = r["herb_name_original"]
        if not name:
            continue
        if name in groups:
            for member in groups[name]:
                hid = resolve(member) or (member if member in by_id else "")
                rows.append({**r, "herb_name_original": name, "herb_id": hid, "from_group": name,
                             "member": member, "qty_percent": ""})
            continue
        hid = r.get("herb_id") or resolve(name)
        if hid and hid not in by_id:
            hid = ""  # an id that isn't in the herbs table can't be trusted
        rows.append({**r, "herb_id": hid, "member": name})

    cols = ["recipe_id", "herb_name_original", "herb_id", "resolved", "item", "member", "from_group", "part_used",
            "qty_original", "unit_original", "qty_percent", "qty_rule"]
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=cols)
    out["resolved"] = out["herb_id"] != ""
    out["item"] = out["herb_id"].where(out["resolved"], out["member"])
    for c in cols:
        if c not in out.columns:
            out[c] = ""
    return out[cols].drop_duplicates(["recipe_id", "item"]).reset_index(drop=True)


def load(data_dir: Path = DATA_DIR) -> KB:
    data_dir = Path(data_dir)
    t, warnings = {}, []
    for name in SCHEMA:
        df, existed = read_table(name, data_dir)
        t[name] = df
        if not existed and name not in ("evidence", "review_log"):
            level = "ไม่พบไฟล์หลัก" if name in CORE_TABLES else "ยังไม่มีข้อมูล"
            warnings.append(f"{level}: {name}.csv")
    for col in ("review_status",):
        for name in ("recipes", "herbs", "herb_synonyms", "herb_groups"):
            t[name][col] = t[name][col].replace("", "pending")
    t["recipes"] = t["recipes"].drop_duplicates("recipe_id")
    for col in ("identity", "availability"):
        t["herb_grades"][col] = t["herb_grades"][col].str.upper()

    meta_path = data_dir / "dataset.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    kb = KB(t=t, meta=meta, warnings=warnings, fingerprint=fingerprint(data_dir))
    kb.items = resolve_items(t)
    return kb


# ---------- writing (back-end edits) ----------

def save_table(name: str, df: pd.DataFrame, data_dir: Path = DATA_DIR) -> None:
    cols = SCHEMA[name] + [c for c in df.columns if c not in SCHEMA[name]]
    df.reindex(columns=cols).fillna("").to_csv(Path(data_dir) / f"{name}.csv", index=False, encoding="utf-8-sig")


def log_review(reviewer: str, action: str, table: str, detail: str, version: str,
               data_dir: Path = DATA_DIR) -> None:
    log, _ = read_table("review_log", data_dir)
    row = {"timestamp": dt.datetime.now().isoformat(timespec="seconds"), "reviewer": reviewer, "action": action,
           "table": table, "detail": detail, "data_version": version}
    save_table("review_log", pd.concat([log, pd.DataFrame([row])], ignore_index=True), data_dir)


SETTINGS_DEFAULT = {
    "research_identity_allowed": ["A", "B", "C"],
    "research_availability_allowed": ["A", "B", "C"],
    "research_set_by": "",
    "weight_symptom": 1.0,
    "weight_indication": 0.5,
    "low_support_count": 5,
}


def settings(data_dir: Path = DATA_DIR) -> dict:
    p = Path(data_dir) / "settings.json"
    s = dict(SETTINGS_DEFAULT)
    if p.exists():
        s.update(json.loads(p.read_text(encoding="utf-8")))
    return s


def save_settings(s: dict, data_dir: Path = DATA_DIR) -> None:
    (Path(data_dir) / "settings.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
