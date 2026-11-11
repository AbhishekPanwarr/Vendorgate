"""World vendor -> VendorSubmission payload (clean baseline for operators)."""

import copy


def submission_for(vendor: dict, spend: int | None = None) -> dict:
    c = vendor["country"]
    tax = {
        "country": c,
        "tax_id_type": "GSTIN" if c == "IN" else "EIN" if c == "US" else "VAT",
        "tax_id": vendor["tax"]["tax_id"],
        "secondary_ids": {},
        "tax_classification": "PVT_LTD" if c == "IN" else "LLC",
        "form_type": vendor["tax"]["form"],
        "vat_id": vendor["tax"]["tax_id"] if c in ("GB", "DE") else None,
    }
    if c == "IN":
        tax["secondary_ids"] = {"PAN": vendor["tax"]["pan"]}
    bank = {
        "country": c,
        "currency": vendor["bank"].get("currency", "USD"),
        "account_holder_name": vendor["legal_name"],
        "bank_name": "Test Bank",
        "account_number": vendor["bank"].get("account_number", "000123456789"),
        "routing_number": vendor["bank"].get("routing_number"),
        "iban": vendor["bank"].get("iban"),
        "swift_bic": None,
        "ifsc": vendor["bank"].get("ifsc"),
        "sort_code": None,
    }
    docs = []
    if c == "US":
        docs = [
            {"doc_id": "d1", "doc_type": "W9", "filename": "w9.pdf", "sha256": "x"},
            {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "bank.pdf", "sha256": "y"},
        ]
    elif c == "IN":
        docs = [
            {"doc_id": "d1", "doc_type": "GST_CERT", "filename": "gst.pdf", "sha256": "x"},
            {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "bank.pdf", "sha256": "y"},
        ]
    else:
        docs = [
            {"doc_id": "d1", "doc_type": "VAT_CERT", "filename": "vat.pdf", "sha256": "x"},
            {"doc_id": "d2", "doc_type": "BANK_LETTER", "filename": "bank.pdf", "sha256": "y"},
        ]
    return {
        "schema_version": "1.0",
        "submission_type": "NEW_VENDOR",
        "existing_vendor_id": None,
        "requester": {
            "name": "Dana Whitfield",
            "email": "dana@buyer.example",
            "department": "Facilities",
            "business_justification": "eval case",
            "expected_annual_spend": {"amount": 3000, "currency": "USD"},
            "category": "OFFICE_SUPPLIES",
            "data_access": False,
            "one_time": False,
        },
        "company": {
            "legal_name": vendor["legal_name"],
            "trading_name": None,
            "entity_type": "LLC",
            "country": c,
            "incorporation_date": f"{vendor['truth']['incorporation_year']}-04-12",
            "registered_address": {
                "line1": "410 Market St",
                "line2": None,
                "city": "Columbus",
                "region": "OH",
                "postal_code": "43215",
                "country": c,
            },
            "remit_to_address": None,
            "website": f"https://{vendor['email'].split('@')[1]}",
            "primary_contact": {
                "name": "Ravi Khanna",
                "email": vendor["email"],
                "phone": vendor["phone"],
            },
            "ap_contact": {"name": "Meera Das", "email": vendor["email"], "phone": vendor["phone"]},
            "owners": [],
        },
        "tax": tax,
        "bank": bank,
        "documents": copy.deepcopy(docs),
        "declarations": {
            "aliases": [],
            "bank_change_justification": None,
            "remit_address_justification": None,
        },
        "submitter_meta": {},
    }
