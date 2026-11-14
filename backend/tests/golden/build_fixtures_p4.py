"""Build Phase 4 delta goldens (run once; committed)."""

import asyncio
import copy
import json

from backend.app.pipeline.pipeline import run_delta
from backend.app.pipeline.pipeline import run_full

PDFS = "backend/tests/fixtures/pdfs"


def _files(*names):
    out = {}
    for n in names:
        with open(f"{PDFS}/{n}", "rb") as fh:
            out[n.split(".")[0].split("_")[0] + n] = (n, fh.read())
    return out


def hp1_delta():
    with open("backend/tests/fixtures/hp1_payload.json") as fh:
        base = json.load(fh)
    r1 = asyncio.run(run_full(base))
    v2 = copy.deepcopy(base)
    v2["company"]["ap_contact"]["email"] = "ap-team@brightline-office.example"
    r2 = asyncio.run(run_delta(base, r1["findings"], v2, version=2, case_id=r1["case_id"]))
    return base, v2, r1, r2


def ec1_delta():
    fx = json.load(open("backend/tests/golden/fixtures/ec-1-run-1.json"))
    base = fx["payload"]
    r1 = asyncio.run(run_full(base))
    v2 = copy.deepcopy(base)
    v2["documents"] = [
        {"doc_id": "w9", "doc_type": "W9", "filename": "w9_ec1.pdf", "sha256": "x"},
        {"doc_id": "bank", "doc_type": "BANK_LETTER", "filename": "bank_hp1.pdf", "sha256": "y"},
        {
            "doc_id": "inc",
            "doc_type": "INCORP_CERT",
            "filename": "incorp_ec1_resubmit.pdf",
            "sha256": "z",
        },
    ]
    files = {}
    for n in ("w9_ec1.pdf", "bank_hp1.pdf", "incorp_ec1_resubmit.pdf"):
        with open(f"{PDFS}/{n}", "rb") as fh:
            files[n] = (n, fh.read())
    keyed = {
        "w9": files["w9_ec1.pdf"],
        "bank": files["bank_hp1.pdf"],
        "inc": files["incorp_ec1_resubmit.pdf"],
    }
    r2 = asyncio.run(
        run_delta(base, r1["findings"], v2, files=keyed, version=2, case_id=r1["case_id"])
    )
    return base, v2, r1, r2


def main() -> None:
    for name, fn in (("hp-1-delta", hp1_delta), ("ec-1-delta", ec1_delta)):
        base, v2, r1, r2 = fn()
        d = r2["decision"]
        print(name, d["status"], d["tier"], d["score"]["total"], "| delta:", r2.get("delta"))
        entry: dict = {
            "payload": v2,
            "base_payload": base,
            "decision": d,
            "findings": r2["findings"],
            "delta": r2.get("delta"),
        }
        if name == "ec-1-delta":
            import base64 as _b64

            entry["files"] = {
                k: [fn_, _b64.b64encode(data).decode()]
                for k, (fn_, data) in {
                    "w9": ("w9_ec1.pdf", open(f"{PDFS}/w9_ec1.pdf", "rb").read()),
                    "bank": ("bank_hp1.pdf", open(f"{PDFS}/bank_hp1.pdf", "rb").read()),
                    "inc": (
                        "incorp_ec1_resubmit.pdf",
                        open(f"{PDFS}/incorp_ec1_resubmit.pdf", "rb").read(),
                    ),
                }.items()
            }
        with open(f"backend/tests/golden/fixtures/{name}.json", "w") as fh:
            json.dump(entry, fh, indent=1)
    print("phase4 delta goldens written")


if __name__ == "__main__":
    main()
