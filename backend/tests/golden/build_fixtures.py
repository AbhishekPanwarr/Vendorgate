"""Build Phase 1 golden fixtures (run once; committed)."""

import asyncio
import copy
import json

from backend.app.pipeline.pipeline import run_full
from backend.app.validators.gstin import gstin_check_char

HP1 = json.load(open("backend/tests/fixtures/hp1_payload.json"))


def in_ids(pan="AAPCA1234F", state="29"):
    base = (state + pan + "1Z")[:14]
    return base + gstin_check_char(base), pan


def base_in():
    b = copy.deepcopy(HP1)
    gstin, pan = in_ids()
    b["requester"].update(
        {
            "expected_annual_spend": {"amount": 30000, "currency": "USD"},
            "category": "CONSULTING",
            "data_access": False,
        }
    )
    b["company"].update(
        {
            "legal_name": "Nimbus Technologies Pvt Ltd",
            "entity_type": "PVT_LTD",
            "country": "IN",
            "incorporation_date": "2019-03-10",
            "registered_address": {
                "line1": "44 Residency Rd",
                "line2": None,
                "city": "Bengaluru",
                "region": "Karnataka",
                "postal_code": "560025",
                "country": "IN",
            },
            "website": "https://nimbus-tech.example",
            "primary_contact": {
                "name": "A",
                "email": "a@nimbus-tech.example",
                "phone": "+91 98765 43210",
            },
            "ap_contact": {
                "name": "B",
                "email": "b@nimbus-tech.example",
                "phone": "+91 98765 43211",
            },
        }
    )
    b["tax"] = {
        "country": "IN",
        "tax_id_type": "GSTIN",
        "tax_id": gstin,
        "secondary_ids": {"PAN": pan},
        "tax_classification": "PVT_LTD",
        "form_type": "GST_CERT",
        "vat_id": None,
    }
    b["bank"] = {
        "country": "IN",
        "currency": "INR",
        "account_holder_name": "Nimbus Technologies Pvt Ltd",
        "bank_name": "Test Bank",
        "account_number": "123456789012",
        "routing_number": None,
        "iban": None,
        "swift_bic": None,
        "ifsc": "HDFC0001234",
        "sort_code": None,
    }
    b["documents"] = [
        {"doc_id": "d1", "doc_type": "GST_CERT", "filename": "gst.pdf", "sha256": "x"},
        {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "bank.pdf", "sha256": "y"},
        {"doc_id": "d3", "doc_type": "INCORP_CERT", "filename": "inc.pdf", "sha256": "z"},
    ]
    return b


def hp3():
    h = copy.deepcopy(HP1)
    h["requester"].update(
        {
            "expected_annual_spend": {"amount": 600000, "currency": "USD"},
            "category": "LOGISTICS",
            "data_access": False,
        }
    )
    h["company"].update(
        {
            "legal_name": "Hafen Logistik GmbH",
            "entity_type": "GMBH",
            "country": "DE",
            "incorporation_date": "2010-02-01",
            "registered_address": {
                "line1": "Am Sandtorkai 1",
                "line2": None,
                "city": "Hamburg",
                "region": "Hamburg",
                "postal_code": "20457",
                "country": "DE",
            },
            "website": "https://hafen-logistik.example",
            "primary_contact": {
                "name": "A",
                "email": "a@hafen-logistik.example",
                "phone": "+49 40 123456",
            },
            "ap_contact": {
                "name": "B",
                "email": "b@hafen-logistik.example",
                "phone": "+49 40 123457",
            },
        }
    )
    h["tax"] = {
        "country": "DE",
        "tax_id_type": "VAT",
        "tax_id": "DE812415868",
        "secondary_ids": {},
        "tax_classification": "GMBH",
        "form_type": "VAT_CERT",
        "vat_id": "DE812415868",
    }
    h["bank"] = {
        "country": "DE",
        "currency": "EUR",
        "account_holder_name": "Hafen Logistik GmbH",
        "bank_name": "Test Bank",
        "account_number": "4053201300",
        "routing_number": None,
        "iban": "DE89370400440532013000",
        "swift_bic": "COBADEFF",
        "ifsc": None,
        "sort_code": None,
    }
    h["documents"] = [
        {"doc_id": "d1", "doc_type": "VAT_CERT", "filename": "vat.pdf", "sha256": "x"},
        {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "bank.pdf", "sha256": "y"},
        {"doc_id": "d3", "doc_type": "INCORP_CERT", "filename": "inc.pdf", "sha256": "z"},
        {"doc_id": "d4", "doc_type": "COI", "filename": "coi.pdf", "sha256": "w"},
    ]
    return h


def ec1():
    e = copy.deepcopy(HP1)
    e["company"]["legal_name"] = "Acme Trading Co"
    e["bank"]["account_holder_name"] = "ACME TRADING COMPANY LLC"
    return e


def ec2a():
    e = base_in()
    e["tax"]["tax_id"] = "84-1234567"
    e["tax"]["secondary_ids"] = {}
    e["documents"] = [d for d in e["documents"] if d["doc_type"] != "INCORP_CERT"]
    return e


def ec2b():
    e = base_in()
    gstin, _ = in_ids()
    bad = gstin[:-1] + ("0" if gstin[-1] != "0" else "1")
    e["tax"]["tax_id"] = bad
    return e


def ec2c():
    e = base_in()
    gstin, _ = in_ids(pan="AAPCA1234F")
    e["tax"]["tax_id"] = gstin
    e["tax"]["secondary_ids"] = {"PAN": "BBBBB1111B"}
    return e


def ec18():
    e = copy.deepcopy(HP1)
    e["tax"]["form_type"] = "W8BEN"
    return e


CASES = {
    "hp-1": HP1,
    "hp-2": json.load(open("backend/tests/fixtures/hp2_payload.json")),
    "hp-3": hp3(),
    "ec-1-run-1": ec1(),
    "ec-2a": ec2a(),
    "ec-2b": ec2b(),
    "ec-2c": ec2c(),
    "ec-18": ec18(),
}

for name, payload in CASES.items():
    r = asyncio.run(run_full(payload))
    d = r["decision"]
    print(name, d["status"], d["tier"], d["score"]["total"], d["reason_codes"])
    json.dump(
        {"payload": payload, "decision": d, "findings": r["findings"]},
        open(f"backend/tests/golden/fixtures/{name}.json", "w"),
        indent=1,
    )
print("fixtures written")
