"""Hand-authored L1 fixtures (verbatim quotes from corpus PDFs; OQ-logged)."""

import json

from backend.app.ingest.text import extract_text_layer
from backend.app.llm.client import cache_key
from backend.app.llm.tasks_extract import L1_SYSTEM
from backend.app.llm.tasks_extract import SCHEMAS
from backend.app.llm.tasks_extract import grounding_ok
from backend.app.llm.tasks_l1 import user_text

MODEL = "muse-spark-1.3"


def F(value, quote, page=1, conf=1.0):
    return {"value": value, "quote": quote, "page": page, "confidence": conf}


def N():
    return {"value": None, "quote": None, "page": None, "confidence": 0.0}


DOCS = {
    ("w9_hp1.pdf", "W9"): {
        "name": N(),
        "business_name": F(
            "Brightline Office Supply LLC", "Name of business: Brightline Office Supply LLC"
        ),
        "tax_classification": F(
            "Limited Liability Company", "Tax classification: Limited Liability Company"
        ),
        "address": N(),
        "tin": F("84-1234567", "Taxpayer Identification Number: 84-1234567"),
        "signature_present": F("/s/ R. Khanna", "Signature: /s/ R. Khanna"),
        "signature_date": F("2026-10-01", "Date: 2026-10-01"),
        "form_revision": F("March 2024", "Form W-9 (Rev. March 2024)"),
    },
    ("w9_ec1.pdf", "W9"): {
        "name": N(),
        "business_name": F("Acme Trading Co.", "Name of business: Acme Trading Co."),
        "tax_classification": F(
            "Limited Liability Company", "Tax classification: Limited Liability Company"
        ),
        "address": N(),
        "tin": F("84-7654321", "Taxpayer Identification Number: 84-7654321"),
        "signature_present": F("/s/ R. Khanna", "Signature: /s/ R. Khanna"),
        "signature_date": F("2026-10-01", "Date: 2026-10-01"),
        "form_revision": F("March 2024", "Form W-9 (Rev. March 2024)"),
    },
    ("bank_hp2.pdf", "BANK_LETTER"): {
        "bank_name": N(),
        "account_holder": F(
            "Nimbus Technologies Pvt Ltd", "Account Holder: Nimbus Technologies Pvt Ltd"
        ),
        "account_number": F("123456789012", "Account Number: 123456789012"),
        "routing": F("HDFC0001234", "IFSC: HDFC0001234"),
        "letter_date": F("2026-09-15", "Letter Date: 2026-09-15"),
        "signatory": F("Branch Manager", "Signatory: Branch Manager"),
        "letterhead_present": N(),
    },
    ("bank_hp3.pdf", "BANK_LETTER"): {
        "bank_name": N(),
        "account_holder": F("Hafen Logistik GmbH", "Account Holder: Hafen Logistik GmbH"),
        "account_number": F("0532013000", "Account Number: 0532013000"),
        "routing": F("DE89370400440532013000", "IBAN: DE89370400440532013000"),
        "letter_date": F("2026-09-15", "Letter Date: 2026-09-15"),
        "signatory": F("Branch Manager", "Signatory: Branch Manager"),
        "letterhead_present": N(),
    },
}

store = {}
for (fn, hint), fields in DOCS.items():
    pages, _ = extract_text_layer(open(f"backend/tests/fixtures/pdfs/{fn}", "rb").read())
    key = cache_key(MODEL, L1_SYSTEM, user_text(hint, pages), SCHEMAS[hint])
    store[key] = dict(fields)
    store[key]["_tokens_used"] = 0
    store[key]["_hand_authored"] = True

with open("backend/tests/fixtures/llm_cache/hand_authored.json", "w") as fh:
    json.dump(store, fh, indent=1)
print("hand-authored keys:", len(store))

# verify every quote is grounded
text_all = {}
bad = 0
for (fn, hint), fields in DOCS.items():
    pages, _ = extract_text_layer(open(f"backend/tests/fixtures/pdfs/{fn}", "rb").read())
    text = "\n".join(pages)
    for name, f in fields.items():
        if not grounding_ok(f["value"], f["quote"], text):
            print("UNGROUNDED", fn, name)
            bad += 1
print("ungrounded:", bad)
