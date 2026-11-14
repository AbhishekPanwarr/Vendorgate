"""Legal-form loading + comparison."""

import re

import yaml

_GENERIC = {"CO"}

_ABBR = {
    "intl": "international",
    "svcs": "services",
    "mfg": "manufacturing",
    "tech": "technology",
    "mgmt": "management",
    "intl.": "international",
}


def load_forms(path: str = "policy/legal_forms.yaml") -> dict[str, list[str]]:
    with open(path) as fh:
        return dict(yaml.safe_load(fh)["forms"])


def canonical_form(token: str, forms: dict[str, list[str]]) -> str | None:
    t = token.strip().lower().rstrip(".")
    for canon, aliases in forms.items():
        if t == canon.lower() or t in [a.lower() for a in aliases]:
            return canon
    return None


def strip_form_suffix(name: str, forms: dict[str, list[str]]) -> tuple[str, str | None]:
    """Longest-match legal suffix strip. Returns (core, canonical_form|None)."""
    s = name.strip()
    cands: list[tuple[str, str]] = []
    for canon, aliases in forms.items():
        for a in [canon, *aliases]:
            cands.append((a, canon))
    cands.sort(key=lambda x: -len(x[0]))
    for alias, canon in cands:
        pat = re.compile(r"[\s,.\-]+(" + re.escape(alias) + r")$", re.IGNORECASE)
        m = pat.search(s)
        if m:
            return s[: m.start()].strip(" ,.-"), canon
    return s, None


def _is_generic(form: str | None) -> bool:
    return form is None or form in _GENERIC


def compare_forms(a: str | None, b: str | None) -> str:
    if _is_generic(a) and _is_generic(b):
        return "COMPATIBLE" if (a is None or b is None or a != b) else "SAME"
    if a == b:
        return "SAME"
    if _is_generic(a) or _is_generic(b):
        return "ASYMMETRIC"
    return "CONFLICT"
