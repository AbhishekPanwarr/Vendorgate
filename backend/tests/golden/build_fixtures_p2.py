"""Build Phase 2 golden fixtures (EC-3a/3b/4a/4b/4d, HP-3-HIGH)."""

import asyncio
import copy
import json

from backend.app.adapters.faults import clear_faults
from backend.app.adapters.faults import set_fault
from backend.app.pipeline.pipeline import run_full

HP1 = json.load(open("backend/tests/fixtures/hp1_payload.json"))


def gb_vendor(name, country, year, spend=30000):
    v = copy.deepcopy(HP1)
    v["requester"].update(
        {"expected_annual_spend": {"amount": spend, "currency": "USD"}, "category": "CONSULTING"}
    )
    v["company"].update(
        {
            "legal_name": name,
            "entity_type": "LTD",
            "country": country,
            "incorporation_date": f"{year}-04-01",
            "registered_address": {
                "line1": "10 Harbour Rd",
                "line2": None,
                "city": "London" if country == "GB" else "Panama City",
                "region": "London",
                "postal_code": "E1 6AN",
                "country": country,
            },
            "website": "https://meridian-shipping.example",
            "primary_contact": {
                "name": "A",
                "email": "a@meridian-shipping.example",
                "phone": "+442071234567",
            },
            "ap_contact": {
                "name": "B",
                "email": "b@meridian-shipping.example",
                "phone": "+442071234568",
            },
        }
    )
    v["tax"] = {
        "country": "GB",
        "tax_id_type": "VAT",
        "tax_id": "GB999999973",
        "secondary_ids": {},
        "tax_classification": "LTD",
        "form_type": "VAT_CERT",
        "vat_id": "GB999999973",
    }
    v["bank"] = {
        "country": "GB",
        "currency": "GBP",
        "account_holder_name": name,
        "bank_name": "Test Bank",
        "account_number": "31926819",
        "routing_number": None,
        "iban": "GB29NWBK60161331926819",
        "swift_bic": "NWBKGB2L",
        "ifsc": None,
        "sort_code": "60-16-13",
    }
    v["documents"] = [
        {"doc_id": "d1", "doc_type": "VAT_CERT", "filename": "v.pdf", "sha256": "x"},
        {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "b.pdf", "sha256": "y"},
        {"doc_id": "d3", "doc_type": "INCORP_CERT", "filename": "i.pdf", "sha256": "z"},
    ]
    return v


def ec3a():
    v = copy.deepcopy(HP1)
    v["company"].update(
        {
            "legal_name": "Northwind Logistics Pvt Ltd",
            "entity_type": "PVT_LTD",
            "country": "IN",
            "incorporation_date": "2021-01-01",
            "registered_address": {
                "line1": "5 Port Rd",
                "line2": None,
                "city": "Mumbai",
                "region": "Maharashtra",
                "postal_code": "400001",
                "country": "IN",
            },
            "website": "https://northwind-logistics.example",
            "primary_contact": {
                "name": "A",
                "email": "a@northwind-logistics.example",
                "phone": "+91 98765 00001",
            },
            "ap_contact": {
                "name": "B",
                "email": "b@northwind-logistics.example",
                "phone": "+91 98765 00002",
            },
        }
    )
    v["tax"] = {
        "country": "IN",
        "tax_id_type": "GSTIN",
        "tax_id": "27BBBBB1111B1ZN",
        "secondary_ids": {"PAN": "BBBBB1111B"},
        "tax_classification": "PVT_LTD",
        "form_type": "GST_CERT",
        "vat_id": None,
    }
    v["bank"] = {
        "country": "IN",
        "currency": "INR",
        "account_holder_name": "Northwind Logistics Pvt Ltd",
        "bank_name": "Test Bank",
        "account_number": "987654321098",
        "routing_number": None,
        "iban": None,
        "swift_bic": None,
        "ifsc": "HDFC0001234",
        "sort_code": None,
    }
    v["documents"] = [
        {"doc_id": "d1", "doc_type": "GST_CERT", "filename": "g.pdf", "sha256": "x"},
        {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "b.pdf", "sha256": "y"},
    ]
    return v


def ec3b():
    v = copy.deepcopy(HP1)
    v["submission_type"] = "CHANGE_REQUEST"
    v["existing_vendor_id"] = "V-000017"
    v["company"].update({"legal_name": "Beacon Retail Group Inc", "entity_type": "CORP"})
    v["tax"] = {
        "country": "US",
        "tax_id_type": "EIN",
        "tax_id": "52-7654321",
        "secondary_ids": {},
        "tax_classification": "CORP",
        "form_type": "W9",
        "vat_id": None,
    }
    v["bank"] = {
        "country": "GB",
        "currency": "GBP",
        "account_holder_name": "Beacon Retail Group Inc",
        "bank_name": "Test Bank",
        "account_number": "31926819",
        "routing_number": None,
        "iban": "GB29NWBK60161331926819",
        "swift_bic": "NWBKGB2L",
        "ifsc": None,
        "sort_code": "60-16-13",
    }
    v["documents"] = [
        {"doc_id": "d1", "doc_type": "W9", "filename": "w.pdf", "sha256": "x"},
        {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "b.pdf", "sha256": "y"},
    ]
    return v


def ec4a():
    v = gb_vendor("Meridian Shipping Svcs LLC", "GB", 2021)
    v["company"]["owners"] = []
    return v


def ec4b():
    v = gb_vendor("Meridian Shipping Svcs LLC", "PA", 2009)
    v["company"]["registered_address"].update(
        {"city": "Panama City", "region": "Panama", "postal_code": "0801", "country": "PA"}
    )
    v["company"]["owners"] = []
    v["bank"]["country"] = "PA"
    v["bank"]["iban"] = None
    v["bank"]["swift_bic"] = None
    return v


def hp3high():
    v = copy.deepcopy(json.load(open("backend/tests/golden/fixtures/hp-3.json"))["payload"])
    v["company"].update(
        {
            "legal_name": "Rhein Bau GmbH",
            "incorporation_date": "2019-06-01",
            "owners": [{"name": "Petra Hoffmann", "ownership_pct": 100, "role": "DIRECTOR"}],
        }
    )
    v["requester"].update({"category": "CONSTRUCTION", "data_access": True})
    v["bank"].update(
        {
            "account_holder_name": "Rhein Bau GmbH",
            "country": "CH",
            "currency": "CHF",
            "account_number": "5271368760195207651",
            "iban": "CH5271368760195207651",
            "swift_bic": "RAIFCH22",
        }
    )
    v["tax"]["tax_id"] = "DE761612490"
    v["tax"]["vat_id"] = "DE761612490"
    v["documents"] = [d for d in v["documents"] if d["doc_type"] != "COI"]
    return v


clear_faults()
CASES = {"ec-3a": ec3a(), "ec-3b": ec3b(), "ec-4a": ec4a(), "ec-4b": ec4b(), "hp-3-high": hp3high()}


def main() -> None:
    for name, payload in CASES.items():
        r = asyncio.run(run_full(payload))
        d = r["decision"]
        print(
            name,
            d["status"],
            d["tier"],
            d["score"]["total"],
            d["reason_codes"],
            "| route:",
            d.get("approval_route"),
        )
        json.dump(
            {"payload": payload, "decision": d, "findings": r["findings"]},
            open(f"backend/tests/golden/fixtures/{name}.json", "w"),
            indent=1,
        )

    # ec-4d: registry outage then restore
    set_fault("registry", "TIMEOUT")
    v = gb_vendor("Meridian Shipping Svcs LLC", "GB", 2021, spend=100000)
    r = asyncio.run(run_full(v))
    d = r["decision"]
    print("ec-4d-outage", d["status"], d["tier"], d["score"]["total"], d["reason_codes"])
    json.dump(
        {"payload": v, "decision": d, "findings": r["findings"]},
        open("backend/tests/golden/fixtures/ec-4d-outage.json", "w"),
        indent=1,
    )
    clear_faults()
    print("fixtures written")


if __name__ == "__main__":
    main()
