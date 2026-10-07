"""Apriori rules engine (mlxtend).

Transaction = one recipe (rows flagged duplicate_of are excluded by default).
Items are typed: HERB:<herb>, SYMPTOM:<symptom>, INDICATION:<indication>.
HERB items are herbs after คณาเภสัช expansion and reviewed-synonym resolution;
an unresolved name is used as written (it is still a real item in the text).

Every result carries its metadata: data version, thresholds, analysis type,
books, duplicate handling, number of transactions (denominator), runtime.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

from core import cache
from core.data import KB

HERB, SYMPTOM, INDICATION = "HERB:", "SYMPTOM:", "INDICATION:"
ANALYSES = {
    "herb_herb": "สมุนไพร ↔ สมุนไพร",
    "symptom_herb": "อาการ → สมุนไพร",
    "indication_herb": "ข้อบ่งใช้ → กลุ่มสมุนไพร",
}
DISCLAIMER = ('กฎ "X → Y" หมายถึงรูปแบบการปรากฏร่วมกันในชุดข้อมูล ไม่ยืนยันว่า X เป็นเหตุของ Y '
              "ไม่พิสูจน์ฤทธิ์เสริมกัน และไม่ใช่โอกาสที่ผู้ป่วยจะหาย")


@dataclass(frozen=True)
class Params:
    analysis: str = "herb_herb"
    min_support: float = 0.03
    min_confidence: float = 0.3
    min_lift: float = 1.0
    books: tuple[str, ...] = ("WRO", "NR", "RM")
    include_duplicates: bool = False
    max_len: int = 3
    low_count: int = 5


def label(item: str) -> str:
    for p in (HERB, SYMPTOM, INDICATION):
        if item.startswith(p):
            return item[len(p):]
    return item


def kind(item: str) -> str:
    return item.split(":", 1)[0] + ":"


def transactions(kb: KB, p: Params) -> pd.DataFrame:
    """Recipes × items boolean matrix for this analysis."""
    rec = kb.recipes[kb.recipes["book"].isin(p.books)]
    if not p.include_duplicates:
        rec = rec[rec["duplicate_of"] == ""]
    # a transaction must have herbs: recipes not yet split into herbs can't take part
    ids = set(rec["recipe_id"]) & set(kb.items["recipe_id"])
    pairs = [kb.items.loc[kb.items["recipe_id"].isin(ids), ["recipe_id", "item"]].assign(item=lambda d: HERB + d["item"])]
    if p.analysis == "symptom_herb":
        s = kb.t["recipe_symptoms"]
        pairs.append(s.loc[s["recipe_id"].isin(ids), ["recipe_id"]].assign(item=SYMPTOM + s["symptom_original"]))
    elif p.analysis == "indication_herb":
        i = kb.t["recipe_indications"]
        pairs.append(i.loc[i["recipe_id"].isin(ids), ["recipe_id"]].assign(item=INDICATION + i["indication"]))
    long = pd.concat(pairs, ignore_index=True)
    if long.empty:
        return pd.DataFrame()
    return pd.crosstab(long["recipe_id"], long["item"]).astype(bool)


def _typed_ok(ante: frozenset, cons: frozenset, analysis: str) -> bool:
    a_kinds, c_kinds = {kind(i) for i in ante}, {kind(i) for i in cons}
    if analysis == "herb_herb":
        return a_kinds == {HERB} and c_kinds == {HERB}
    if analysis == "symptom_herb":
        return a_kinds == {SYMPTOM} and c_kinds == {HERB} and len(cons) == 1
    if analysis == "indication_herb":
        return a_kinds == {INDICATION} and c_kinds == {HERB}
    raise ValueError(analysis)


RULE_COLS = ["antecedent", "consequent", "antecedent_items", "consequent_items", "count", "support", "confidence",
             "lift", "low_data"]


def compute(kb: KB, p: Params) -> tuple[pd.DataFrame, dict]:
    start = time.perf_counter()
    X = transactions(kb, p)
    n = len(X)
    meta = {**asdict(p), "books": list(p.books), "data_version": kb.version, "n_transactions": n,
            "analysis_label": ANALYSES[p.analysis]}
    if n == 0:
        return pd.DataFrame(columns=RULE_COLS), {**meta, "runtime_sec": 0.0, "note": "ไม่มีตำรับที่แยกสมุนไพรแล้ว"}
    freq = apriori(X, min_support=p.min_support, use_colnames=True, max_len=p.max_len)
    if len(freq) == 0 or freq["itemsets"].map(len).max() < 2:
        return pd.DataFrame(columns=RULE_COLS), {**meta, "runtime_sec": round(time.perf_counter() - start, 3)}
    r = association_rules(freq, num_itemsets=n, metric="lift", min_threshold=p.min_lift)
    r = r[r["confidence"] >= p.min_confidence]
    typed = [_typed_ok(a, c, p.analysis) for a, c in zip(r["antecedents"], r["consequents"])]
    r = r.loc[pd.Series(typed, index=r.index, dtype=bool)]
    if r.empty:
        return pd.DataFrame(columns=RULE_COLS), {**meta, "runtime_sec": round(time.perf_counter() - start, 3)}
    out = pd.DataFrame({
        "antecedent": r["antecedents"].map(lambda s: " + ".join(sorted(label(i) for i in s))),
        "consequent": r["consequents"].map(lambda s: " + ".join(sorted(label(i) for i in s))),
        "antecedent_items": r["antecedents"].map(lambda s: tuple(sorted(label(i) for i in s))),
        "consequent_items": r["consequents"].map(lambda s: tuple(sorted(label(i) for i in s))),
        "count": (r["support"] * n).round().astype(int),
        "support": r["support"], "confidence": r["confidence"], "lift": r["lift"],
    })
    out["low_data"] = out["count"] < p.low_count
    out = out.sort_values(["lift", "count"], ascending=False, ignore_index=True)
    return out, {**meta, "runtime_sec": round(time.perf_counter() - start, 3)}


def cached_rules(kb: KB, p: Params) -> tuple[pd.DataFrame, dict]:
    """Same data + same params → read from disk, don't recompute."""
    return cache.cached("rules", kb.fingerprint, asdict(p), lambda: compute(kb, p))


DEFAULTS = {a: Params(analysis=a) for a in ANALYSES}


def precompute(kb: KB) -> None:
    for p in DEFAULTS.values():
        cached_rules(kb, p)


def sensitivity(kb: KB, analysis: str, supports: list[float], confidences: list[float]) -> pd.DataFrame:
    rows = []
    for c in confidences:
        for s in supports:
            r, _ = cached_rules(kb, Params(analysis=analysis, min_support=s, min_confidence=c))
            rows.append({"min_support": s, "min_confidence": c, "rules": len(r)})
    return pd.DataFrame(rows)
