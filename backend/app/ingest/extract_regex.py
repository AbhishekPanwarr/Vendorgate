"""Deterministic regex field extraction (wins over LLM on disagreement)."""

import re

PATTERNS = {
    "GSTIN": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"),
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "EIN": re.compile(r"\b\d{2}-\d{7}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    "VATID": re.compile(r"\b(?:GB|DE)\d{9}\b"),
    "IFSC": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    "ROUTING": re.compile(r"\bRouting[:\s#]*(\d{9})\b", re.IGNORECASE),
    "DATE": re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b"),
    "ACCOUNT": re.compile(r"\bAccount(?: Number| No\.?)?[:\s#]*(\d{4,18})\b", re.IGNORECASE),
}


def extract(text: str) -> dict[str, list[tuple[str, str]]]:
    """Returns {field: [(value, quote)]} with a ≤200-char quote window."""
    out: dict[str, list[tuple[str, str]]] = {}
    for field, pat in PATTERNS.items():
        hits = []
        for m in pat.finditer(text):
            val = m.group(1) if m.lastindex else m.group(0)
            start = max(0, m.start() - 80)
            quote = text[start : m.end() + 80][:200]
            hits.append((val, quote))
        if hits:
            out[field] = hits
    return out
