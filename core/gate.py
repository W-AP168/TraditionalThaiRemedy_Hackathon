"""Readiness gate (spec section 5).

Every herb of a recipe must pass BOTH axes. No averaging: one failing or
ungraded herb fails the whole recipe. Relevance is a separate output and never
compensates for a failing herb.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from core.data import KB

PASS, FAIL, INSUFFICIENT = "ผ่าน", "ไม่ผ่าน", "ข้อมูลไม่พอ"


@dataclass(frozen=True)
class Mode:
    key: str
    identity_allowed: tuple[str, ...]
    availability_allowed: tuple[str, ...]
    label: str
    industry: bool


INDUSTRY = Mode("industry", ("A", "B"), ("A",), "พร้อมพัฒนาระดับอุตสาหกรรม", True)


def research_mode(settings: dict) -> Mode:
    return Mode("research", tuple(settings["research_identity_allowed"]),
                tuple(settings["research_availability_allowed"]),
                "ผ่านเกณฑ์วิจัย (เกณฑ์ตั้งโดยผู้เชี่ยวชาญ ไม่ใช่ระดับอุตสาหกรรม)", False)


@dataclass
class HerbCheck:
    herb_name_original: str
    herb_id: str
    from_group: str
    identity: str
    availability: str
    identity_ok: bool | None      # None = no data
    availability_ok: bool | None
    problems: list[str] = field(default_factory=list)


@dataclass
class GateResult:
    recipe_id: str
    identity_status: str
    availability_status: str
    ready: bool
    herbs: list[HerbCheck]

    @property
    def limiting(self) -> list[HerbCheck]:
        return [h for h in self.herbs if h.problems]


def _status(oks: list[bool | None]) -> str:
    if not oks or any(o is None for o in oks):
        return INSUFFICIENT
    return PASS if all(oks) else FAIL


def check_herbs(herbs: pd.DataFrame, grades: pd.DataFrame, mode: Mode) -> tuple[str, str, list[HerbCheck]]:
    g = grades.drop_duplicates("herb_id").set_index("herb_id") if not grades.empty else pd.DataFrame()
    checks = []
    for r in herbs.to_dict("records"):
        hid = r["herb_id"]
        idg = avg = ""
        if hid and hid in g.index:
            idg, avg = g.at[hid, "identity"], g.at[hid, "availability"]
        problems = []
        if not hid:
            problems.append("ชื่อสมุนไพรยังไม่ยืนยัน (รอตรวจสอบ)")
            id_ok = av_ok = None
        else:
            id_ok = (idg in mode.identity_allowed) if idg else None
            av_ok = (avg in mode.availability_allowed) if avg else None
            if id_ok is None:
                problems.append("ยังไม่มีเกรด Identity")
            elif not id_ok:
                problems.append(f"Identity {idg} ไม่อยู่ในเกณฑ์ ({'/'.join(mode.identity_allowed)})")
            if av_ok is None:
                problems.append("ยังไม่มีเกรด Availability")
            elif not av_ok:
                problems.append(f"Availability {avg} ไม่อยู่ในเกณฑ์ ({'/'.join(mode.availability_allowed)})")
        checks.append(HerbCheck(r["herb_name_original"], hid, r.get("from_group", ""), idg, avg, id_ok, av_ok,
                                problems))
    return _status([c.identity_ok for c in checks]), _status([c.availability_ok for c in checks]), checks


def evaluate(kb: KB, recipe_id: str, mode: Mode) -> GateResult:
    ids, avs, checks = check_herbs(kb.herbs_of(recipe_id), kb.t["herb_grades"], mode)
    return GateResult(recipe_id, ids, avs, ids == PASS and avs == PASS, checks)
