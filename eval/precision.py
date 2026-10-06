"""Precision@5: system vs plain keyword search (spec section 9).

Inputs from the experts, set IN ADVANCE and held out from tuning:
  data/eval_queries.csv  query_id, symptoms, indications   (terms separated by ,)
  data/eval_labels.csv   query_id, recipe_id, relevant      (1 = relevant, 0 = not)

Relevance is whatever the experts labelled; recipes they did not label count as
not relevant (stated in the UI).
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from core.data import DATA_DIR, KB, BOOKS
from core.scoring import keyword_baseline, match, precision_at_k, split_terms

QUERY_COLS = ["query_id", "symptoms", "indications"]
LABEL_COLS = ["query_id", "recipe_id", "relevant"]


def load_inputs(data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    q, l = Path(data_dir) / "eval_queries.csv", Path(data_dir) / "eval_labels.csv"
    read = lambda p: pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig") if p.exists() else None
    return read(q), read(l)


def run(kb: KB, queries: pd.DataFrame, labels: pd.DataFrame, k: int = 5,
        w_symptom: float = 1.0, w_indication: float = 0.5) -> pd.DataFrame:
    rel = labels[labels["relevant"].astype(str).str.strip() == "1"].groupby("query_id")["recipe_id"].apply(set)
    rows = []
    for q in queries.to_dict("records"):
        syms, inds = split_terms(q.get("symptoms", "")), split_terms(q.get("indications", ""))
        t0 = time.perf_counter()
        system = [m.recipe_id for m in match(kb, syms, inds, list(BOOKS), w_symptom, w_indication)]
        ms = (time.perf_counter() - t0) * 1000
        base = keyword_baseline(kb, syms + inds, list(BOOKS))
        relevant = rel.get(q["query_id"], set())
        rows.append({"query_id": q["query_id"], "คำค้น": ", ".join(syms + inds), "relevant ที่ติดป้าย": len(relevant),
                     f"P@{k} ระบบ": precision_at_k(system, relevant, k),
                     f"P@{k} keyword": precision_at_k(base, relevant, k), "เวลาค้น (ms)": round(ms, 1)})
    return pd.DataFrame(rows)


def template() -> tuple[str, str]:
    q = pd.DataFrame([{"query_id": "Q1", "symptoms": "ไอ, มีเสมหะ", "indications": ""},
                      {"query_id": "Q2", "symptoms": "ปวดข้อ", "indications": ""}], columns=QUERY_COLS)
    l = pd.DataFrame([{"query_id": "Q1", "recipe_id": "NR003/1", "relevant": "1"}], columns=LABEL_COLS)
    return q.to_csv(index=False), l.to_csv(index=False)
