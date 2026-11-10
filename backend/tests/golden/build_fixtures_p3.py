"""Build Phase 3 goldens: EC-1-resubmit (files), EC-4c, EC-5, EC-6, EC-16."""

import asyncio
import copy
import json

from backend.app.pipeline.pipeline import run_full

PDFS = "backend/tests/fixtures/pdfs"


def pdf(doc_id):
    with open(f"{PDFS}/{doc_id}", "rb") as fh:
        return (doc_id, fh.read())


def ec4c():
    base = json.load(open("backend/tests/golden/fixtures/ec-4b.json"))["payload"]
    v = copy.deepcopy(base)
    v["company"].update(
        {"legal_name": "Meridian Shippin Svcs LLC", "incorporation_date": "2021-04-01"}
    )
    v["bank"]["account_holder_name"] = "Meridian Shippin Svcs LLC"
    v["documents"] = [
        {"doc_id": "coi", "doc_type": "COI", "filename": "coi_ec4c.pdf", "sha256": "x"}
    ]
    files = {"coi": pdf("coi_ec4c.pdf")}
    return v, files


def ec5():
    base = json.load(open("backend/tests/fixtures/hp1_payload.json"))
    v = copy.deepcopy(base)
    v["documents"] = [
        {"doc_id": "w9", "doc_type": "W9", "filename": "w9_hp1.pdf", "sha256": "x"},
        {
            "doc_id": "bank",
            "doc_type": "BANK_LETTER",
            "filename": "bank_ec5_hidden.pdf",
            "sha256": "y",
        },
    ]
    files = {"w9": pdf("w9_hp1.pdf"), "bank": pdf("bank_ec5_hidden.pdf")}
    return v, files


def ec6():
    v = copy.deepcopy(json.load(open("backend/tests/fixtures/hp1_payload.json")))
    v["company"]["legal_name"] = "Аcme Trading LLC"
    v["bank"]["account_holder_name"] = "Аcme Trading LLC"
    v["tax"]["tax_id"] = "84-7654321"
    return v, {}


def ec16():
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    blank = "/tmp/blank.pdf"
    c = canvas.Canvas(blank, pagesize=letter)
    c.showPage()
    c.save()
    with open(blank, "rb") as fh:
        data = fh.read()
    v = copy.deepcopy(json.load(open("backend/tests/fixtures/hp1_payload.json")))
    v["documents"] = [{"doc_id": "w9", "doc_type": "W9", "filename": "blank.pdf", "sha256": "x"}]
    return v, {"w9": ("blank.pdf", data)}


def ec1resubmit():
    base = json.load(open("backend/tests/golden/fixtures/ec-1-run-1.json"))["payload"]
    v = copy.deepcopy(base)
    v["documents"] = [
        {"doc_id": "w9", "doc_type": "W9", "filename": "w9_ec1.pdf", "sha256": "x"},
        {"doc_id": "bank", "doc_type": "BANK_LETTER", "filename": "bank_hp1.pdf", "sha256": "y"},
        {
            "doc_id": "inc",
            "doc_type": "INCORP_CERT",
            "filename": "incorp_ec1_resubmit.pdf",
            "sha256": "z",
        },
    ]
    files = {
        "w9": pdf("w9_ec1.pdf"),
        "bank": pdf("bank_hp1.pdf"),
        "inc": pdf("incorp_ec1_resubmit.pdf"),
    }
    return v, files


CASES = {
    "ec-1-resubmit": ec1resubmit(),
    "ec-4c": ec4c(),
    "ec-5": ec5(),
    "ec-6": ec6(),
    "ec-16": ec16(),
}


def main() -> None:
    for name, (payload, files) in CASES.items():
        r = asyncio.run(run_full(payload, files=files))
        d = r["decision"]
        print(
            name,
            d["status"],
            d["tier"],
            d["score"]["total"],
            d["reason_codes"],
            "| awaiting:",
            d["awaiting"],
        )
        import base64

        json.dump(
            {
                "payload": payload,
                "files": {k: [fn, base64.b64encode(data).decode()] for k, (fn, data) in files.items()},
                "decision": d,
                "findings": r["findings"],
            },
            open(f"backend/tests/golden/fixtures/{name}.json", "w"),
            indent=1,
        )
    print("phase3 fixtures written")


if __name__ == "__main__":
    main()
