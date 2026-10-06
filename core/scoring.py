"""Relevance score for Recommend (spec section 5).

NOT defined in the concept paper → default proposal, weights configurable in
the back-end and shown in the UI:

    score = (w_s × matched_symptoms / queried_symptoms + w_i × matched_indications / queried_indications)
            / (sum of the weights of the parts that were queried)

Exact term match only (no substring: "ตา" must not match "ปวดตามข้อ").
A symptom matches on symptom_original or on a reviewed symptom_modern.
The score is agreement with the database, NOT a probability of treatment success.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.data import KB, clean


@dataclass
class Match:
    recipe_id: str
    score: float
    sym_matched: list[str]
    sym_total: int
    ind_matched: list[str]
    ind_total: int

    @property
    def breakdown(self) -> str:
        parts = []
        if self.sym_total:
            parts.append(f"ตรง {len(self.sym_matched)}/{self.sym_total} อาการ")
        if self.ind_total:
            parts.append(f"ข้อบ่งใช้ตรง {len(self.ind_matched)}/{self.ind_total}")
        return ", ".join(parts)


def split_terms(text: str) -> list[str]:
    import re
    return [clean(t) for t in re.split(r"[,;/\n、]+", text or "") if clean(t)]


def match(kb: KB, symptoms: list[str], indications: list[str], books: list[str],
          w_symptom: float = 1.0, w_indication: float = 0.5) -> list[Match]:
    q_s = list(dict.fromkeys(s for s in symptoms if s))
    q_i = list(dict.fromkeys(i for i in indications if i))
    if not q_s and not q_i:
        return []
    rec = kb.recipes[kb.recipes["book"].isin(books)]
    sym = kb.t["recipe_symptoms"]
    sym_by = {}
    for rid, orig, modern in zip(sym["recipe_id"], sym["symptom_original"], sym["symptom_modern"]):
        sym_by.setdefault(rid, set()).update(x for x in (orig, modern) if x)
    ind = kb.t["recipe_indications"]
    ind_by = ind.groupby("recipe_id")["indication"].apply(set).to_dict()

    weights = (w_symptom if q_s else 0) + (w_indication if q_i else 0)
    out = []
    for rid in rec["recipe_id"]:
        ms = [s for s in q_s if s in sym_by.get(rid, ())]
        mi = [i for i in q_i if i in ind_by.get(rid, ())]
        if not ms and not mi:
            continue
        raw = (w_symptom * len(ms) / len(q_s) if q_s else 0) + (w_indication * len(mi) / len(q_i) if q_i else 0)
        out.append(Match(rid, raw / weights if weights else 0, ms, len(q_s), mi, len(q_i)))
    return sorted(out, key=lambda m: (-m.score, -len(m.sym_matched) - len(m.ind_matched), m.recipe_id))


def keyword_baseline(kb: KB, terms: list[str], books: list[str]) -> list[str]:
    """Plain keyword search for evaluation: count substring hits in the recipe text."""
    rec = kb.recipes[kb.recipes["book"].isin(books)]
    sym = kb.t["recipe_symptoms"].groupby("recipe_id")["symptom_original"].apply(" ".join)
    scored = []
    for r in rec.itertuples(index=False):
        text = " ".join([r.name, r.indication_text, r.original_text, sym.get(r.recipe_id, "")])
        hits = sum(text.count(t) for t in terms if t)
        if hits:
            scored.append((hits, r.recipe_id))
    return [rid for _, rid in sorted(scored, key=lambda x: (-x[0], x[1]))]


def precision_at_k(ranked: list[str], relevant: set[str], k: int = 5) -> float:
    top = ranked[:k]
    return sum(r in relevant for r in top) / k if k else 0.0


def unknown_terms(kb: KB, symptoms: list[str], indications: list[str]) -> list[str]:
    vocab = set(kb.symptom_terms()) | set(kb.indication_terms())
    return [t for t in symptoms + indications if t not in vocab]


def to_frame(matches: list[Match]) -> pd.DataFrame:
    return pd.DataFrame([{"recipe_id": m.recipe_id, "score": m.score, "breakdown": m.breakdown} for m in matches])
