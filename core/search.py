"""Symptom and herb search.

Match score ("ความสอดคล้องกับข้อมูลอาการ") = share of the selected symptoms
that the recipe lists. It describes agreement with the database, NOT
clinical efficacy. Ties are broken by Jaccard similarity, so a recipe
focused on the chosen symptoms ranks above one that lists many others.
"""

from __future__ import annotations

import pandas as pd

from core.data_loader import Dataset, normalize_name


def search_by_symptoms(ds: Dataset, symptoms: list[str], scriptures: list[str] | None = None) -> pd.DataFrame:
    wanted = {normalize_name(s) for s in symptoms if normalize_name(s)}
    cols = ["recipe_id", "name_th", "scripture_id", "matched", "n_matched", "score", "jaccard"]
    if not wanted:
        return pd.DataFrame(columns=cols)

    by_recipe = ds.symptoms.groupby("recipe_id")["symptom"].apply(set)
    rows = []
    for rid, have in by_recipe.items():
        hit = wanted & have
        if hit:
            rows.append({
                "recipe_id": rid,
                "matched": sorted(hit),
                "n_matched": len(hit),
                "score": len(hit) / len(wanted),
                "jaccard": len(hit) / len(wanted | have),
            })
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows).merge(ds.prescriptions[["recipe_id", "name_th", "scripture_id"]], on="recipe_id")
    if scriptures:
        out = out[out["scripture_id"].isin(scriptures)]
    return out.sort_values(["score", "jaccard"], ascending=False, ignore_index=True)[cols]


def search_recipes(ds: Dataset, text: str = "", scriptures: list[str] | None = None) -> pd.DataFrame:
    """Browse: match recipe id, recipe name, or any herb name/synonym."""
    pres = ds.prescriptions.copy()
    if scriptures:
        pres = pres[pres["scripture_id"].isin(scriptures)]
    q = normalize_name(text)
    if q:
        herb_hit = ds.ingredients.loc[
            ds.ingredients["herb_id"].str.contains(q, regex=False)
            | ds.ingredients["herb_raw"].str.contains(q, regex=False),
            "recipe_id",
        ]
        mask = (
            pres["recipe_id"].str.contains(q, case=False, regex=False)
            | pres["name_th"].str.contains(q, regex=False)
            | pres["recipe_id"].isin(herb_hit)
        )
        pres = pres[mask]
    n_herbs = ds.ingredients.groupby("recipe_id").size().rename("n_herbs")
    return pres.merge(n_herbs, left_on="recipe_id", right_index=True, how="left").fillna({"n_herbs": 0})


def recipes_with_herb(ds: Dataset, herb_id: str) -> pd.DataFrame:
    ids = ds.ingredients.loc[ds.ingredients["herb_id"] == herb_id, "recipe_id"]
    return ds.prescriptions[ds.prescriptions["recipe_id"].isin(ids)]


def symptoms_for_herb(ds: Dataset, herb_id: str, top: int = 8) -> pd.Series:
    ids = recipes_with_herb(ds, herb_id)["recipe_id"]
    return ds.symptoms[ds.symptoms["recipe_id"].isin(ids)]["symptom"].value_counts().head(top)


def symptoms_for_pair(ds: Dataset, a: str, b: str, top: int = 8) -> tuple[list[str], pd.Series]:
    ing = ds.ingredients
    both = set(ing.loc[ing["herb_id"] == a, "recipe_id"]) & set(ing.loc[ing["herb_id"] == b, "recipe_id"])
    sym = ds.symptoms[ds.symptoms["recipe_id"].isin(both)]["symptom"].value_counts().head(top)
    return sorted(both), sym
