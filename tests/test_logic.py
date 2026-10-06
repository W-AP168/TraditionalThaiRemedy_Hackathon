from itertools import combinations

import pytest

from core import rules as R
from core.data import load
from core.gate import FAIL, INDUSTRY, INSUFFICIENT, PASS, Mode, check_herbs
from core.scoring import keyword_baseline, match, precision_at_k
from core.similarity import compare, jaccard, similar
from eval import gate_fixtures


@pytest.fixture(scope="module")
def kb():
    return load()  # committed sample dataset


# ---------- rules ----------

def test_rules_are_typed_and_carry_metadata(kb):
    for analysis in R.ANALYSES:
        r, meta = R.compute(kb, R.Params(analysis=analysis))
        assert meta["n_transactions"] > 0 and meta["data_version"] == kb.version
        assert {"min_support", "min_confidence", "min_lift", "books", "include_duplicates"} <= set(meta)
        if analysis == "symptom_herb" and len(r):
            sym = set(kb.t["recipe_symptoms"]["symptom_original"])
            assert all(set(a) <= sym for a in r["antecedent_items"])
            assert all(len(c) == 1 for c in r["consequent_items"])


def test_rule_counts_match_brute_force(kb):
    p = R.Params()
    r, meta = R.compute(kb, p)
    X = R.transactions(kb, p)
    X.columns = [R.label(c) for c in X.columns]
    for row in r.head(20).itertuples():
        items = list(row.antecedent_items) + list(row.consequent_items)
        assert int(X[items].all(axis=1).sum()) == row.count
        assert row.support == pytest.approx(row.count / meta["n_transactions"])


def test_duplicates_excluded_by_default(kb):
    n_dup = int((kb.recipes["duplicate_of"] != "").sum())
    assert n_dup > 0
    a = len(R.transactions(kb, R.Params()))
    b = len(R.transactions(kb, R.Params(include_duplicates=True)))
    assert b - a == n_dup


def test_unsplit_books_have_no_transactions(kb):
    assert R.transactions(kb, R.Params(books=("RM",))).empty


# ---------- gate ----------

def test_gate_fixtures_all_correct():
    res = gate_fixtures.run()
    assert res["ถูกต้อง"].all(), res.to_string()


def test_gate_no_averaging():
    import pandas as pd
    herbs = pd.DataFrame([{"herb_name_original": h, "herb_id": h, "from_group": ""} for h in "abcde"])
    grades = pd.DataFrame([{"herb_id": h, "identity": "A", "availability": "A"} for h in "abcd"]
                          + [{"herb_id": "e", "identity": "A", "availability": "D"}])
    ids, avs, checks = check_herbs(herbs, grades, INDUSTRY)
    assert (ids, avs) == (PASS, FAIL)
    assert [c.herb_name_original for c in checks if c.problems] == ["e"]


def test_gate_unresolved_herb_is_insufficient():
    import pandas as pd
    herbs = pd.DataFrame([{"herb_name_original": "x", "herb_id": "", "from_group": ""}])
    ids, avs, _ = check_herbs(herbs, pd.DataFrame(columns=["herb_id", "identity", "availability"]), INDUSTRY)
    assert ids == avs == INSUFFICIENT


def test_research_mode_uses_its_own_criteria():
    import pandas as pd
    herbs = pd.DataFrame([{"herb_name_original": "a", "herb_id": "a", "from_group": ""}])
    grades = pd.DataFrame([{"herb_id": "a", "identity": "C", "availability": "C"}])
    assert check_herbs(herbs, grades, INDUSTRY)[:2] == (FAIL, FAIL)
    research = Mode("research", ("A", "B", "C"), ("A", "B", "C"), "r", False)
    assert check_herbs(herbs, grades, research)[:2] == (PASS, PASS)


# ---------- scoring / similarity ----------

def test_exact_match_not_substring(kb):
    # the old app matched "ตา" inside "ปวดตามข้อ": exact matching must not
    assert match(kb, ["ปวด"], [], ["WRO", "NR", "RM"]) == []
    assert keyword_baseline(kb, ["ปวด"], ["WRO", "NR", "RM"])  # the baseline does substring, on purpose


def test_relevance_score(kb):
    ms = match(kb, ["ไอ", "มีเสมหะ"], [], ["WRO", "NR", "RM"])
    assert ms and all(0 < m.score <= 1 for m in ms)
    assert ms == sorted(ms, key=lambda m: -m.score)
    full = [m for m in ms if len(m.sym_matched) == 2]
    assert all(m.score == 1 for m in full)


def test_precision_and_jaccard(kb):
    assert precision_at_k(["a", "b", "c", "d", "e", "f"], {"a", "c", "z"}, 5) == pytest.approx(0.4)
    assert jaccard({1, 2}, {2, 3}) == pytest.approx(1 / 3)
    rid = kb.items["recipe_id"].iloc[0]
    sim = similar(kb, rid)
    assert (sim["jaccard"].diff().dropna() <= 0).all()
    c = compare(kb, rid, sim["recipe_id"].iloc[0])
    assert c["jaccard"] == pytest.approx(sim["jaccard"].iloc[0])
