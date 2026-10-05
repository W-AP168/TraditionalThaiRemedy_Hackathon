"""Load the cleaned dataset from data/ into one Dataset object.

Data model:  SCRIPTURE → PRESCRIPTION → (SYMPTOM, INGREDIENT → HERB)
Every ingredient name is mapped to its canonical herb_id through
herb_synonyms.csv, so "ขิงแห้ง" and "ขิง" count as the same herb.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REQUIRED_FILES = {
    "scriptures": ["scripture_id", "name_th"],
    "prescriptions": ["recipe_id", "scripture_id", "name_th"],
    "ingredients": ["recipe_id", "herb_raw"],
    "symptoms": ["recipe_id", "symptom"],
    "herbs": ["herb_id", "sci_name"],
    "herb_synonyms": ["synonym", "herb_id"],
}


@dataclass
class Dataset:
    scriptures: pd.DataFrame
    prescriptions: pd.DataFrame
    ingredients: pd.DataFrame  # has herb_id after synonym mapping
    symptoms: pd.DataFrame
    herbs: pd.DataFrame
    synonyms: pd.DataFrame
    symptom_groups: pd.DataFrame
    meta: dict = field(default_factory=dict)
    fingerprint: str = ""

    @property
    def n_recipes(self) -> int:
        return len(self.prescriptions)

    @property
    def n_herbs(self) -> int:
        return self.ingredients["herb_id"].nunique()

    @property
    def n_scriptures(self) -> int:
        return self.prescriptions["scripture_id"].nunique()

    @property
    def n_symptoms(self) -> int:
        return self.symptoms["symptom"].nunique()

    def recipe(self, recipe_id: str) -> pd.Series:
        return self.prescriptions.set_index("recipe_id").loc[recipe_id]

    def herbs_of(self, recipe_id: str) -> pd.DataFrame:
        ing = self.ingredients[self.ingredients["recipe_id"] == recipe_id]
        return ing.merge(self.herbs, on="herb_id", how="left")

    def symptoms_of(self, recipe_id: str) -> list[str]:
        return self.symptoms.loc[self.symptoms["recipe_id"] == recipe_id, "symptom"].tolist()


def normalize_name(name: object) -> str:
    """Trim spaces and unify whitespace in a Thai name."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return " ".join(str(name).split())


def apply_synonyms(names: pd.Series, synonyms: pd.DataFrame) -> pd.Series:
    mapping = dict(zip(synonyms["synonym"].map(normalize_name), synonyms["herb_id"].map(normalize_name)))
    cleaned = names.map(normalize_name)
    return cleaned.map(lambda n: mapping.get(n, n))


def _read(data_dir: Path, name: str) -> pd.DataFrame:
    path = data_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"missing {path.name} in {data_dir}")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED_FILES.get(name, []) if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(missing)}")
    return df


def fingerprint(data_dir: Path = DATA_DIR) -> str:
    """Hash of every CSV in data/. Changes whenever the data changes."""
    h = hashlib.sha256()
    for p in sorted(data_dir.glob("*.csv")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def load_dataset(data_dir: Path = DATA_DIR) -> Dataset:
    data_dir = Path(data_dir)
    tables = {name: _read(data_dir, name) for name in REQUIRED_FILES}

    ing = tables["ingredients"].copy()
    ing["herb_id"] = apply_synonyms(ing["herb_raw"], tables["herb_synonyms"])
    ing = ing[ing["herb_id"] != ""].drop_duplicates(["recipe_id", "herb_id"])

    sym = tables["symptoms"].copy()
    sym["symptom"] = sym["symptom"].map(normalize_name)
    sym = sym[sym["symptom"] != ""].drop_duplicates()

    groups_path = data_dir / "symptom_groups.csv"
    if groups_path.exists():
        groups = pd.read_csv(groups_path, dtype=str, keep_default_na=False)
    else:
        groups = pd.DataFrame({"symptom": sorted(sym["symptom"].unique()), "symptom_group": "อื่น ๆ"})

    herbs = tables["herbs"].copy()
    for col, default in (("safety_level", "none"), ("safety_note", "")):
        if col not in herbs.columns:
            herbs[col] = default
    herbs["safety_level"] = herbs["safety_level"].replace("", "none")

    pres = tables["prescriptions"].copy()
    for col in ("form", "original_text", "page_ref"):
        if col not in pres.columns:
            pres[col] = ""

    meta_path = data_dir / "dataset.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    return Dataset(
        scriptures=tables["scriptures"],
        prescriptions=pres,
        ingredients=ing,
        symptoms=sym,
        herbs=herbs,
        synonyms=tables["herb_synonyms"],
        symptom_groups=groups,
        meta=meta,
        fingerprint=fingerprint(data_dir),
    )
