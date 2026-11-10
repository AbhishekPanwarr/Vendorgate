"""Name parsing + comparison (thresholds always from policy)."""

import re
from dataclasses import dataclass

from unidecode import unidecode

from backend.app.matching.legal_forms import _ABBR
from backend.app.matching.legal_forms import compare_forms
from backend.app.matching.legal_forms import load_forms
from backend.app.matching.legal_forms import strip_form_suffix
from backend.app.matching.normalize import canon_text
from backend.app.matching.similarity import core_similarity
from backend.app.matching.similarity import is_initialism


@dataclass
class NameParts:
    raw: str
    core: str
    tokens: list[str]
    form: str | None
    qualifiers: list[str]


@dataclass
class NameComparison:
    relation: str
    core_sim: float
    form_rel: str


def parse_name(raw: str, forms: dict[str, list[str]] | None = None) -> NameParts:
    forms = forms or load_forms()
    canon, _ = canon_text(raw)
    s = unidecode(canon)
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    core, form = strip_form_suffix(s, forms)
    toks = []
    for t in core.split():
        toks.append(_ABBR.get(t, t))
    return NameParts(raw=raw, core=" ".join(toks), tokens=toks, form=form, qualifiers=[])


_GENERIC_TOKENS = {
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "ltd",
    "limited",
    "llc",
    "llp",
    "plc",
    "gmbh",
    "ag",
    "pvt",
    "private",
}


def _strip_generics(core: str) -> str:
    toks = [t for t in core.split() if t not in _GENERIC_TOKENS]
    return " ".join(toks)


def _canon_raw(a: str) -> str:
    c, _ = canon_text(a)
    return c


def _core_sim(x: str, y: str, cap: float) -> float:
    best = core_similarity(x, y, subset_cap=cap)
    sx, sy = _strip_generics(x), _strip_generics(y)
    if sx and sy and (sx, sy) != (x, y):
        best = max(best, core_similarity(sx, sy, subset_cap=cap))
    return best


def compare_names(a: NameParts, b: NameParts, cfg: dict[str, float]) -> NameComparison:
    t_hi = float(cfg["t_hi"])
    t_lo = float(cfg["t_lo"])
    cap = float(cfg.get("subset_cap", 0.88))
    s = _core_sim(a.core, b.core, cap)
    f = compare_forms(a.form, b.form)
    if s >= t_hi:
        if _canon_raw(a.raw) == _canon_raw(b.raw):
            rel = "EXACT"
        elif f in ("SAME", "COMPATIBLE"):
            rel = "EQUIVALENT"
        else:
            rel = "FORM_CONFLICT"
    elif s >= t_lo or is_initialism(a.core, b.core):
        rel = "CORE_FUZZY"
    else:
        rel = "DIFFERENT"
    return NameComparison(relation=rel, core_sim=s, form_rel=f)
