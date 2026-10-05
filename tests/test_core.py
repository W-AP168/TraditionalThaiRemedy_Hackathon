import numpy as np
import pandas as pd
import pytest

from core.apriori import apriori, association_rules, binary_matrix, filter_rules, herb_pairs
from core.data_loader import apply_synonyms, load_dataset
from core.safety import recipe_flags, recipe_level
from core.search import search_by_symptoms
from core.statistics import benjamini_hochberg, permutation_test
from preprocessing.make_sample_data import generate
from preprocessing.prepare_data import prepare, publish


@pytest.fixture()
def data_dir(tmp_path):
    for name, df in generate(n_recipes=80).items():
        df.to_csv(tmp_path / f"{name}.csv", index=False)
    return tmp_path


@pytest.fixture()
def ds(data_dir):
    return load_dataset(data_dir)


def toy_matrix():
    # 10 recipes; A and B always together in the first 4
    rows = [{"A", "B"}] * 4 + [{"A"}, {"C"}, {"C", "B"}, {"C"}, {"D"}, {"D", "C"}]
    items = ["A", "B", "C", "D"]
    return pd.DataFrame([[i in r for i in items] for r in rows], columns=items)


def test_synonyms_map_to_canonical_name():
    syn = pd.DataFrame({"synonym": ["ขิงแห้ง"], "herb_id": ["ขิง"]})
    assert apply_synonyms(pd.Series([" ขิงแห้ง ", "ดีปลี"]), syn).tolist() == ["ขิง", "ดีปลี"]


def test_loader_applies_synonyms(ds):
    assert "ขิงแห้ง" not in set(ds.ingredients["herb_id"])
    assert not ds.ingredients.duplicated(["recipe_id", "herb_id"]).any()


def test_apriori_support_confidence_lift():
    m = toy_matrix()
    its = apriori(m, min_support=0.3)
    sup = dict(zip(its["itemset"], its["support"]))
    assert sup[frozenset({"A", "B"})] == pytest.approx(0.4)
    rules = association_rules(its, len(m))
    r = rules[(rules["antecedent"] == "A") & (rules["consequent"] == "B")].iloc[0]
    assert r["confidence"] == pytest.approx(4 / 5)
    assert r["lift"] == pytest.approx((4 / 5) / 0.5)


def test_apriori_matches_brute_force(ds):
    m = binary_matrix(ds)
    its = apriori(m, 0.08, max_len=3)
    X = m.to_numpy()
    for s, sup in zip(its["itemset"], its["support"]):
        cols = [m.columns.get_loc(i) for i in s]
        assert X[:, cols].all(axis=1).mean() == pytest.approx(sup)


def test_symptom_rules_have_symptom_antecedents(ds):
    m = binary_matrix(ds, include_symptoms=True)
    r = filter_rules(association_rules(apriori(m, 0.05), len(m), 0.3, 1.0), "symptom")
    assert not r.empty
    assert r["antecedent"].str.startswith("อาการ:").all()
    assert not r["consequent"].str.startswith("อาการ:").any()


def test_herb_pairs_lift_matches_rules():
    p = herb_pairs(toy_matrix(), min_count=1)
    ab = p[(p["a"] == "A") & (p["b"] == "B")].iloc[0]
    assert ab["lift"] == pytest.approx(0.4 / (0.5 * 0.5))


def test_permutation_detects_planted_pair():
    rng = np.random.default_rng(1)
    n = 200
    a = rng.random(n) < 0.3
    b = a & (rng.random(n) < 0.9) | (rng.random(n) < 0.05)
    noise = rng.random(n) < 0.3
    m = pd.DataFrame({"A": a, "B": b, "N": noise})
    assert permutation_test(m, "A", "B", n_perm=500)["p_value"] < 0.01
    assert permutation_test(m, "A", "N", n_perm=500)["p_value"] > 0.05


def test_permutation_keeps_marginals():
    t = permutation_test(toy_matrix(), "A", "B", n_perm=200)
    # under the null, lift averages ~1
    assert t["null_mean"] == pytest.approx(1.0, abs=0.15)
    assert 0 < t["p_value"] <= 1


def test_bh_monotone_and_bounded():
    q = benjamini_hochberg([0.01, 0.04, 0.03, 0.5])
    assert np.all(q >= np.array([0.01, 0.04, 0.03, 0.5]) - 1e-12)
    assert q.max() <= 1
    assert q[0] == pytest.approx(0.04)


def test_symptom_search_ranks_full_match_first(ds):
    res = search_by_symptoms(ds, ["ไข้", "ตัวร้อน"])
    assert not res.empty
    assert res["score"].is_monotonic_decreasing
    assert res.iloc[0]["score"] == 1.0
    assert (res["score"] <= 1).all()


def test_safety_flags(ds):
    ing = ds.ingredients
    rid = ing.loc[ing["herb_id"] == "ไคร้เครือ", "recipe_id"].iloc[0]
    assert "ไคร้เครือ" in set(recipe_flags(ds, rid)["herb_id"])
    assert recipe_level(ds, rid) == "danger"


def test_prepare_and_publish(data_dir):
    sheets = {n: pd.read_csv(data_dir / f"{n}.csv", dtype=str) for n in ("prescriptions", "ingredients", "symptoms")}
    sheets["ingredients"].loc[0, "herb_raw"] = ""
    sheets["ingredients"].loc[1, "herb_raw"] = "สมุนไพรไม่รู้จัก"
    rep = prepare(sheets, data_dir)
    by = {c.step: c for c in rep.checks}
    assert by["validate"].ok
    assert not by["missing_herb"].ok
    assert not by["unmapped"].ok
    assert rep.can_publish  # warnings only
    publish(rep, "1.0", "test", data_dir)
    assert load_dataset(data_dir).meta["version"] == "1.0"


def test_prepare_blocks_duplicate_ids(data_dir):
    sheets = {n: pd.read_csv(data_dir / f"{n}.csv", dtype=str) for n in ("prescriptions", "ingredients", "symptoms")}
    p = sheets["prescriptions"]
    sheets["prescriptions"] = pd.concat([p, p.head(1)])
    assert not prepare(sheets, data_dir).can_publish
