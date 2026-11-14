"""Deterministic doc-type anchors (C-DOC-03)."""

ANCHORS: dict[str, list[str]] = {
    "W9": [
        "Request for Taxpayer Identification Number",
        "Form W-9",
        "Taxpayer Identification Number",
    ],
    "W8BEN": ["Certificate of Foreign Status", "Form W-8BEN", "foreign status"],
    "W8BENE": ["Certificate of Foreign Status of Beneficial Owner", "Form W-8BEN-E"],
    "GST_CERT": ["GST", "Registration Certificate", "GSTIN", "Goods and Services Tax"],
    "VAT_CERT": ["VAT", "registration certificate", "VAT identification", "USt-IdNr"],
    "INCORP_CERT": ["Certificate of Incorporation", "incorporated", "registration no"],
    "BANK_LETTER": ["bank", "account", "this is to certify", "confirm", "account holder"],
    "VOIDED_CHEQUE": ["void", "cheque", "account number", "MICR"],
    "COI": ["Certificate of Liability Insurance", "Named Insured", "Policy", "insurer"],
    "TRADE_LICENSE": ["Trade License", "licence no", "commercial registration"],
}


def classify(text: str, tau: float = 0.60, delta: float = 0.15) -> tuple[str, float, bool]:
    """Returns (doc_type, score, confident). Score = matched/total anchors."""
    low = text.lower()
    scored = []
    for dtype, anchors in ANCHORS.items():
        hits = sum(1 for a in anchors if a.lower() in low)
        scored.append((dtype, hits / len(anchors)))
    scored.sort(key=lambda x: -x[1])
    top, second = scored[0], scored[1]
    confident = top[1] >= tau and (top[1] - second[1]) >= delta
    return top[0], round(top[1], 3), confident
