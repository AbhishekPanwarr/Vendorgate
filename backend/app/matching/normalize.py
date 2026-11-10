"""Canonicalization helpers. mixed_script is computed on raw text BEFORE unidecode."""

import re
import unicodedata

import phonenumbers
from unidecode import unidecode

_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff\u202a-\u202e]")

_ABBR = {
    "st": "street",
    "rd": "road",
    "ave": "avenue",
    "ste": "suite",
    "blvd": "boulevard",
    "dr": "drive",
}

_FX_USD = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "INR": 0.012}


def _is_latin(ch: str) -> bool:
    return "LATIN" in unicodedata.name(ch, "")


def _is_cyrillic_greek(ch: str) -> bool:
    name = unicodedata.name(ch, "")
    return "CYRILLIC" in name or "GREEK" in name


def has_mixed_script(token: str) -> bool:
    """True if a single token mixes Latin with Cyrillic/Greek lookalikes."""
    norm = unicodedata.normalize("NFC", token)
    kinds = set()
    for ch in norm:
        if not ch.isalpha():
            continue
        if _is_latin(ch):
            kinds.add("latin")
        elif _is_cyrillic_greek(ch):
            kinds.add("other")
    return kinds == {"latin", "other"}


def canon_text(value: str | None) -> tuple[str, bool]:
    """Returns (canonical, mixed_script). mixed_script computed pre-unidecode."""
    raw = value or ""
    raw = unicodedata.normalize("NFC", raw)
    mixed = any(has_mixed_script(tok) for tok in raw.split())
    s = _ZERO_WIDTH.sub("", raw)
    s = unidecode(s)
    s = s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s, mixed


def canon_id(value: str | None) -> str:
    s = unicodedata.normalize("NFC", value or "")
    s = _ZERO_WIDTH.sub("", s).upper()
    return re.sub(r"[\s\-.]", "", s)


def canon_phone(value: str | None, country: str) -> str | None:
    try:
        num = phonenumbers.parse(value or "", country)
    except Exception:
        return None
    if not phonenumbers.is_possible_number(num):
        return None
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def canon_address(value: dict[str, object] | None) -> str:
    if not value:
        return ""
    parts = [
        str(value.get(k, "") or "")
        for k in ("line1", "line2", "city", "region", "postal_code", "country")
    ]
    s = " ".join(parts)
    s, _ = canon_text(s)
    for short, full in _ABBR.items():
        s = re.sub(rf"\b{short}\b", full, s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def canon_domain(value: str | None) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"^https?://", "", s).split("/")[0]
    if s.startswith("www."):
        s = s[4:]
    return s.split("@")[-1]


def canon_money(amount: float, currency: str) -> float:
    return round(float(amount) * _FX_USD.get((currency or "USD").upper(), 1.0), 2)
