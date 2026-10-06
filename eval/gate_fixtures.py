"""Readiness gate test (spec section 9): 3 fixture recipes in a tiny KB.

  FX-PASS        every herb graded inside Industry criteria          → ผ่าน
  FX-ONE-FAIL    one herb has Availability C, best relevance (3/3)   → ไม่ผ่าน, limiting herb shown
  FX-INCOMPLETE  one herb has no grade                               → ข้อมูลไม่พอ

FX-ONE-FAIL matches the query best, to prove relevance never overrides the gate.
Used by tests/ and by the back-end evaluation dashboard.
"""

from __future__ import annotations

import pandas as pd

from core.data import KB, SCHEMA, resolve_items
from core.gate import FAIL, INDUSTRY, INSUFFICIENT, PASS
from core.recommend import recommend

QUERY = ["ไอ", "มีเสมหะ", "เจ็บคอ"]

EXPECTED = {  # recipe → (identity_status, availability_status, limiting herb)
    "FX-PASS": (PASS, PASS, None),
    "FX-ONE-FAIL": (PASS, FAIL, "สมุนไพรค"),
    "FX-INCOMPLETE": (INSUFFICIENT, INSUFFICIENT, "สมุนไพรง"),
}


def fixture_kb() -> KB:
    def df(name, rows):
        return pd.DataFrame(rows, columns=SCHEMA[name]).fillna("")

    t = {name: pd.DataFrame(columns=cols) for name, cols in SCHEMA.items()}
    t["recipes"] = df("recipes", [
        {"recipe_id": rid, "book": "NR", "name": rid, "review_status": "verified"} for rid in EXPECTED])
    herbs = {"FX-PASS": ["สมุนไพรก", "สมุนไพรข"], "FX-ONE-FAIL": ["สมุนไพรก", "สมุนไพรค"],
             "FX-INCOMPLETE": ["สมุนไพรก", "สมุนไพรง"]}
    t["recipe_herbs"] = df("recipe_herbs", [{"recipe_id": r, "herb_name_original": h}
                                            for r, hs in herbs.items() for h in hs])
    t["herbs"] = df("herbs", [{"herb_id": h, "std_name_th": h, "review_status": "verified"}
                              for h in ("สมุนไพรก", "สมุนไพรข", "สมุนไพรค", "สมุนไพรง")])
    t["herb_grades"] = df("herb_grades", [
        {"herb_id": "สมุนไพรก", "identity": "A", "availability": "A", "source": "fixture"},
        {"herb_id": "สมุนไพรข", "identity": "B", "availability": "A", "source": "fixture"},
        {"herb_id": "สมุนไพรค", "identity": "A", "availability": "C", "source": "fixture"},
    ])  # สมุนไพรง: no grade
    t["recipe_symptoms"] = df("recipe_symptoms", [
        {"recipe_id": "FX-PASS", "symptom_original": "ไอ"},
        {"recipe_id": "FX-ONE-FAIL", "symptom_original": "ไอ"},
        {"recipe_id": "FX-ONE-FAIL", "symptom_original": QUERY[1]},
        {"recipe_id": "FX-ONE-FAIL", "symptom_original": "เจ็บคอ"},
        {"recipe_id": "FX-INCOMPLETE", "symptom_original": "ไอ"},
    ])
    kb = KB(t=t, meta={"version": "fixture"})
    kb.items = resolve_items(t)
    return kb


def run() -> pd.DataFrame:
    """One row per fixture: expected vs actual, and whether it is correct."""
    kb = fixture_kb()
    ready, limited = recommend(kb, QUERY, [], ["NR"], INDUSTRY)
    rows = []
    for group, recs in (("ready", ready), ("limited", limited)):
        for r in recs:
            exp_id, exp_av, exp_lim = EXPECTED[r.gate.recipe_id]
            lim = [h.herb_name_original for h in r.gate.limiting]
            ok = (r.gate.identity_status, r.gate.availability_status) == (exp_id, exp_av) and \
                 (lim == ([exp_lim] if exp_lim else [])) and (group == ("ready" if exp_lim is None else "limited"))
            rows.append({"recipe_id": r.gate.recipe_id, "กลุ่ม": group, "relevance": round(r.match.score, 2),
                         "identity": r.gate.identity_status, "availability": r.gate.availability_status,
                         "limiting": ", ".join(lim), "ถูกต้อง": ok})
    top_relevance = max(rows, key=lambda x: x["relevance"])["recipe_id"]
    rows.append({"recipe_id": "(relevance ไม่ชนะ gate)", "กลุ่ม": "", "relevance": None, "identity": "",
                 "availability": "", "limiting": f"relevance สูงสุด = {top_relevance}",
                 "ถูกต้อง": top_relevance == "FX-ONE-FAIL" and all(r.gate.recipe_id != top_relevance for r in ready)})
    return pd.DataFrame(rows)
