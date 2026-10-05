"""Binary matrix + Apriori + association rules.

Binary matrix: one row per recipe, one column per item, True when the
recipe contains that item. Items are herb names, and optionally symptoms
written as "อาการ:<name>".

    support(A)       = recipes with A / all recipes
    confidence(A→B)  = support(A ∪ B) / support(A)
    lift(A→B)        = confidence(A→B) / support(B)
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from core.data_loader import Dataset

SYMPTOM_PREFIX = "อาการ:"


def binary_matrix(ds: Dataset, include_symptoms: bool = False) -> pd.DataFrame:
    """Recipes × items boolean matrix."""
    pairs = ds.ingredients[["recipe_id", "herb_id"]].rename(columns={"herb_id": "item"})
    if include_symptoms:
        sym = ds.symptoms[["recipe_id", "symptom"]].rename(columns={"symptom": "item"})
        sym = sym.assign(item=SYMPTOM_PREFIX + sym["item"])
        pairs = pd.concat([pairs, sym], ignore_index=True)
    m = pd.crosstab(pairs["recipe_id"], pairs["item"]).astype(bool)
    # recipes with no ingredients still count in the denominator
    return m.reindex(ds.prescriptions["recipe_id"], fill_value=False)


def apriori(matrix: pd.DataFrame, min_support: float, max_len: int = 3) -> pd.DataFrame:
    """Frequent itemsets with support ≥ min_support (level-wise Apriori)."""
    X = matrix.to_numpy(dtype=bool)
    n = X.shape[0]
    items = list(matrix.columns)
    if n == 0:
        return pd.DataFrame(columns=["itemset", "count", "support"])
    min_count = int(np.ceil(min_support * n - 1e-9))

    col_counts = X.sum(axis=0)
    frequent = {(i,): X[:, i] for i in range(len(items)) if col_counts[i] >= max(min_count, 1)}
    results = [(k, int(v.sum())) for k, v in frequent.items()]

    level = frequent
    for size in range(2, max_len + 1):
        keys = sorted(level)
        nxt = {}
        for a_idx in range(len(keys)):
            for b_idx in range(a_idx + 1, len(keys)):
                a, b = keys[a_idx], keys[b_idx]
                if a[:-1] != b[:-1]:
                    break  # keys are sorted, so no later b shares the prefix
                cand = a + (b[-1],)
                # Apriori pruning: every subset must be frequent
                if any(sub not in level for sub in combinations(cand, size - 1)):
                    continue
                mask = level[a] & X[:, b[-1]]
                c = int(mask.sum())
                if c >= max(min_count, 1):
                    nxt[cand] = mask
                    results.append((cand, c))
        if not nxt:
            break
        level = nxt

    df = pd.DataFrame(
        [(frozenset(items[i] for i in k), c, c / n) for k, c in results],
        columns=["itemset", "count", "support"],
    )
    return df.sort_values("support", ascending=False, ignore_index=True)


def association_rules(
    itemsets: pd.DataFrame,
    n_recipes: int,
    min_confidence: float = 0.0,
    min_lift: float = 0.0,
) -> pd.DataFrame:
    """Rules A → B from frequent itemsets. B is always a single item."""
    support = dict(zip(itemsets["itemset"], itemsets["support"]))
    counts = dict(zip(itemsets["itemset"], itemsets["count"]))
    rows = []
    for itemset, sup in support.items():
        if len(itemset) < 2:
            continue
        for consequent in itemset:
            antecedent = itemset - {consequent}
            sa, sb = support.get(antecedent), support.get(frozenset([consequent]))
            if not sa or not sb:
                continue
            conf = sup / sa
            lift = conf / sb
            if conf >= min_confidence and lift >= min_lift:
                rows.append({
                    "antecedent": " + ".join(sorted(antecedent)),
                    "consequent": consequent,
                    "antecedent_set": antecedent,
                    "count": counts[itemset],
                    "n": n_recipes,
                    "support": sup,
                    "confidence": conf,
                    "lift": lift,
                })
    cols = ["antecedent", "consequent", "antecedent_set", "count", "n", "support", "confidence", "lift"]
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["lift", "confidence"], ascending=False, ignore_index=True)


def filter_rules(rules: pd.DataFrame, kind: str) -> pd.DataFrame:
    """kind: 'herb' (herb ↔ herb), 'symptom' (symptoms → herb), 'all'."""
    if kind == "all" or rules.empty:
        return rules
    ant_sym = rules["antecedent_set"].map(lambda s: all(i.startswith(SYMPTOM_PREFIX) for i in s))
    ant_herb = rules["antecedent_set"].map(lambda s: not any(i.startswith(SYMPTOM_PREFIX) for i in s))
    con_herb = ~rules["consequent"].str.startswith(SYMPTOM_PREFIX)
    if kind == "herb":
        return rules[ant_herb & con_herb].reset_index(drop=True)
    if kind == "symptom":
        return rules[ant_sym & con_herb].reset_index(drop=True)
    raise ValueError(kind)


def herb_pairs(matrix: pd.DataFrame, min_count: int = 2) -> pd.DataFrame:
    """Every herb pair seen together in ≥ min_count recipes, with lift.

    Symmetric, so each pair appears once (a < b). Used by the knowledge graph
    and the statistics page.
    """
    cols = [c for c in matrix.columns if not c.startswith(SYMPTOM_PREFIX)]
    X = matrix[cols].to_numpy(dtype=np.int32)
    n = X.shape[0]
    co = X.T @ X
    single = np.diag(co)
    rows = []
    for i, j in zip(*np.triu_indices(len(cols), k=1)):
        c = int(co[i, j])
        if c >= min_count:
            lift = (c / n) / ((single[i] / n) * (single[j] / n))
            rows.append({"a": cols[i], "b": cols[j], "count": c, "support": c / n,
                         "count_a": int(single[i]), "count_b": int(single[j]), "lift": lift})
    out = pd.DataFrame(rows, columns=["a", "b", "count", "support", "count_a", "count_b", "lift"])
    return out.sort_values("lift", ascending=False, ignore_index=True)
