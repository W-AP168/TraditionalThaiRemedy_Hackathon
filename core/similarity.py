"""Similar recipes: Jaccard similarity on herb sets (after คณาเภสัช expansion).

Not defined in the concept paper → default proposal, confirm with the team.
"""

from __future__ import annotations

import pandas as pd

from core.data import KB


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def similar(kb: KB, recipe_id: str, top: int = 5, include_duplicates: bool = True) -> pd.DataFrame:
    target = kb.herb_set(recipe_id)
    if not target:
        return pd.DataFrame(columns=["recipe_id", "jaccard", "shared"])
    sets = kb.items.groupby("recipe_id")["item"].apply(set)
    rec = kb.recipes.set_index("recipe_id")
    rows = []
    for rid, s in sets.items():
        if rid == recipe_id:
            continue
        if not include_duplicates and rid in rec.index and rec.at[rid, "duplicate_of"] == recipe_id:
            continue
        j = jaccard(target, s)
        if j > 0:
            rows.append({"recipe_id": rid, "jaccard": j, "shared": len(target & s)})
    out = pd.DataFrame(rows, columns=["recipe_id", "jaccard", "shared"])
    return out.sort_values(["jaccard", "shared"], ascending=False, ignore_index=True).head(top)


def compare(kb: KB, a: str, b: str) -> dict[str, list[str]]:
    sa, sb = kb.herb_set(a), kb.herb_set(b)
    return {"both": sorted(sa & sb), "only_a": sorted(sa - sb), "only_b": sorted(sb - sa),
            "jaccard": jaccard(sa, sb)}
