"""Extraction test set: 120 docs (60 text-layer + 60 scanned) with ground truth."""

import json
import random
from pathlib import Path

from datagen.render_docs import degrade_pdf, doc_sha, render_pdf

OUT = Path("datagen/extraction_set")


def build(seed=42):
    rng = random.Random(seed)
    with open("datagen/out/world.json") as fh:
        world = json.load(fh)
    vendors = [v for v in world["vendors"] if "-B" not in v["vendor_id"]]
    doctypes = ["W9", "GST_CERT", "VAT_CERT", "BANK_LETTER", "COI", "INCORP_CERT"]
    (OUT / "text_layer").mkdir(parents=True, exist_ok=True)
    (OUT / "scanned").mkdir(parents=True, exist_ok=True)
    gt = []
    for i in range(120):
        v = rng.choice([x for x in vendors
                        if (x["country"] == "US") == (doctypes[i % 6] == "W9"
                        and True)][:1] or vendors)
        v = rng.choice(vendors)
        dt = doctypes[i % 6]
        if dt == "W9" and v["country"] != "US":
            v = rng.choice([x for x in vendors if x["country"] == "US"])
        if dt == "GST_CERT" and v["country"] != "IN":
            v = rng.choice([x for x in vendors if x["country"] == "IN"])
        vals = {"business_name": v["legal_name"],
                "tax_classification": "Limited Liability Company",
                "tin": v["tax"]["tax_id"], "signature_present": "/s/ Owner",
                "signature_date": "2026-10-01", "form_revision": "March 2024",
                "legal_name": v["legal_name"], "gstin": v["tax"]["tax_id"],
                "trade_name": v["legal_name"], "state": v["tax"]["tax_id"][:2],
                "registration_date": "2020-05-01", "status": "Active",
                "address": "410 Market St", "vat_id": v["tax"]["tax_id"],
                "effective_date": "2016-04-12", "registration_no": "1",
                "incorporation_date": "2016-04-12", "registered_address": "x",
                "account_holder": v["legal_name"],
                "account_number": v["bank"].get("account_number", "1"),
                "routing": v["bank"].get("routing_number") or v["bank"].get("ifsc") or "",
                "letter_date": "2026-09-15", "signatory": "Branch Manager",
                "insured_name": v["legal_name"], "insurer": "Test General",
                "policy_no": "GL-1", "expiry_date": "2027-06-01",
                "certificate_holder": "Buyer Corp", "name": v["legal_name"],
                "country": v["country"]}
        pdf = render_pdf(dt, vals)
        scanned = i >= 60
        if scanned:
            pdf = degrade_pdf(pdf, seed=i)
        sub = "scanned" if scanned else "text_layer"
        (OUT / sub / f"doc-{i:03d}.pdf").write_bytes(pdf)
        from datagen.render_docs import LAYOUTS

        rendered_fields = {f for _label, f in LAYOUTS[dt] if f}
        truth = {k: v2 for k, v2 in vals.items()
                 if v2 and k in rendered_fields}
        gt.append({"id": f"doc-{i:03d}", "doc_type": dt, "scanned": scanned,
                   "sha256": doc_sha(pdf), "truth": truth})
    with open(OUT / "ground_truth.json", "w") as fh:
        json.dump(gt, fh, indent=1)
    print(f"extraction set: {len(gt)} docs")


if __name__ == "__main__":
    build()
