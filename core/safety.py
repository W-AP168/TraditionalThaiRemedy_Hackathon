"""Safety flags per herb and per recipe (from herbs.csv)."""

from __future__ import annotations

import pandas as pd

from core.data_loader import Dataset

LEVEL_ORDER = {"none": 0, "caution": 1, "danger": 2}
LEVEL_LABEL = {"none": "ไม่พบข้อระวัง", "caution": "ข้อควรระวัง", "danger": "อันตราย"}

DISCLAIMER = (
    "ข้อมูลนี้เป็นการนำข้อมูลจากตำรับยาโบราณมาจัดโครงสร้างเพื่อการศึกษาและวิจัย "
    "ไม่ใช่คำแนะนำในการรักษาโรค ควรปรึกษาแพทย์แผนไทยก่อนใช้"
)


def recipe_flags(ds: Dataset, recipe_id: str) -> pd.DataFrame:
    """Herbs in the recipe that carry a caution or danger note."""
    herbs = ds.herbs_of(recipe_id)
    flagged = herbs[herbs["safety_level"].isin(["caution", "danger"])]
    return flagged[["herb_id", "sci_name", "safety_level", "safety_note"]].reset_index(drop=True)


def recipe_level(ds: Dataset, recipe_id: str) -> str:
    flags = recipe_flags(ds, recipe_id)
    if flags.empty:
        return "none"
    return max(flags["safety_level"], key=LEVEL_ORDER.get)


def all_recipe_levels(ds: Dataset) -> pd.Series:
    """recipe_id → worst safety level, for list views."""
    merged = ds.ingredients.merge(ds.herbs[["herb_id", "safety_level"]], on="herb_id", how="left")
    merged["rank"] = merged["safety_level"].map(LEVEL_ORDER).fillna(0)
    worst = merged.groupby("recipe_id")["rank"].max()
    inv = {v: k for k, v in LEVEL_ORDER.items()}
    levels = worst.map(inv)
    return levels.reindex(ds.prescriptions["recipe_id"], fill_value="none")
