"""Is a herb pair stronger than chance? Permutation test + FDR.

Null model: shuffle herb B across recipes (column permutation). This keeps
how often A and B are each used, and breaks any link between them. Repeat
n times to get the lift values chance alone produces, then ask how often
chance reaches the observed lift.

    p = (1 + #{null lift ≥ observed lift}) / (1 + n_permutations)

The +1 stops p from ever being exactly 0, which a finite test can't claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def permutation_test(
    matrix: pd.DataFrame, a: str, b: str, n_perm: int = 1000, seed: int = 0
) -> dict:
    x = matrix[a].to_numpy(dtype=bool)
    y = matrix[b].to_numpy(dtype=bool)
    n, ca, cb = len(x), int(x.sum()), int(y.sum())
    observed = int((x & y).sum())
    if ca == 0 or cb == 0:
        raise ValueError(f"{a} or {b} never appears")

    rng = np.random.default_rng(seed)
    shuffled = rng.permuted(np.tile(y, (n_perm, 1)), axis=1)
    null_counts = (shuffled & x).sum(axis=1)
    scale = n / (ca * cb)
    null_lift = null_counts * scale
    obs_lift = observed * scale

    return {
        "a": a,
        "b": b,
        "n": n,
        "count": observed,
        "count_a": ca,
        "count_b": cb,
        "observed_lift": obs_lift,
        "null_lift": null_lift,
        "null_mean": float(null_lift.mean()),
        "n_perm": n_perm,
        "p_value": (1 + int((null_counts >= observed).sum())) / (1 + n_perm),
    }


def benjamini_hochberg(p_values: pd.Series | np.ndarray) -> np.ndarray:
    """FDR-adjusted q-values (Benjamini–Hochberg)."""
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    if m == 0:
        return p
    order = np.argsort(p)
    ranked = p[order] * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(q, 0, 1)
    return out


def run_pair_tests(
    matrix: pd.DataFrame, pairs: pd.DataFrame, n_perm: int = 1000, seed: int = 0
) -> pd.DataFrame:
    """Permutation test every row of `pairs` (columns a, b) and add q-values."""
    rows = []
    for i, r in enumerate(pairs.itertuples(index=False)):
        t = permutation_test(matrix, r.a, r.b, n_perm=n_perm, seed=seed + i)
        rows.append({"a": r.a, "b": r.b, "count": t["count"], "observed_lift": t["observed_lift"],
                     "null_mean": t["null_mean"], "p_value": t["p_value"]})
    out = pd.DataFrame(rows, columns=["a", "b", "count", "observed_lift", "null_mean", "p_value"])
    out["q_value"] = benjamini_hochberg(out["p_value"])
    return out.sort_values(["p_value", "observed_lift"], ascending=[True, False], ignore_index=True)


def interpret(p_value: float, q_value: float | None = None, alpha: float = 0.05) -> str:
    """Plain Thai sentence for the result. Never claims efficacy."""
    sig = (q_value if q_value is not None else p_value) < alpha
    if sig:
        return ("ปรากฏร่วมกันมากกว่าที่คาดจากการสุ่มภายใต้แบบจำลองที่ใช้ทดสอบ "
                "อาจสะท้อนรูปแบบการตั้งตำรับที่เกิดซ้ำ ควรศึกษาต่อ")
    return "ยังไม่พบหลักฐานว่าปรากฏร่วมกันมากกว่าความบังเอิญ"
