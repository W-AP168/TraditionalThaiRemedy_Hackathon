"""Recommend = match → readiness gate on every herb → two groups.

1. ผ่านเกณฑ์เพื่อพัฒนา (ready), ranked by relevance
2. ตรงโจทย์แต่ยังมีข้อจำกัด (limited), each with its limiting herbs
Relevance only orders recipes WITHIN a group; it never moves a recipe between groups.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.data import KB
from core.gate import GateResult, Mode, evaluate
from core.scoring import Match, match


@dataclass
class Rec:
    match: Match
    gate: GateResult


def recommend(kb: KB, symptoms: list[str], indications: list[str], books: list[str], mode: Mode,
              w_symptom: float = 1.0, w_indication: float = 0.5) -> tuple[list[Rec], list[Rec]]:
    ready, limited = [], []
    for m in match(kb, symptoms, indications, books, w_symptom, w_indication):
        g = evaluate(kb, m.recipe_id, mode)
        (ready if g.ready else limited).append(Rec(m, g))
    return ready, limited
