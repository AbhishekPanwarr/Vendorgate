"""Prompt-injection scan (C-DOC-08): patterns + hidden-text signals."""

import io
import re

import yaml

_PATTERNS = [
    r"(ignore|disregard).{0,40}(previous|above|prior).{0,20}(instruction|rule|prompt)",
    r"system prompt",
    r"you are (now )?(an? )?(ai|assistant|model)",
    r"(approve|verify|clear|whitelist) (this|the) vendor",
    r"do not (flag|report|escalate)",
    r"mark (as )?(approved|verified|low risk)",
]


def load_patterns(path: str = "policy/injection_patterns.yaml") -> list[str]:
    try:
        with open(path) as fh:
            return list(yaml.safe_load(fh)["patterns"])
    except FileNotFoundError:
        return list(_PATTERNS)


def scan_text(text: str, patterns: list[str] | None = None) -> list[str]:
    hits = []
    for pat in patterns or _PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            hits.append(pat)
    return hits


def hidden_text_signals(data: bytes) -> list[str]:
    """Detect tiny/white-on-white text via pdfplumber char metadata."""
    import pdfplumber

    signals = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                for ch in page.chars:
                    size = float(ch.get("size", 12))
                    color = ch.get("non_stroking_color", ch.get("stroking_color", 0))
                    if size < 2:
                        signals.append(f"hidden-tiny-text p{page.page_number}")
                        break
                    if isinstance(color, (list, tuple)) and len(color) == 3:
                        if all(c > 0.97 for c in color):
                            signals.append(f"hidden-white-text p{page.page_number}")
                            break
                else:
                    continue
                break
    except Exception:
        pass
    return signals


def scan_document(data: bytes, text: str) -> list[str]:
    return scan_text(text, load_patterns()) + hidden_text_signals(data)
