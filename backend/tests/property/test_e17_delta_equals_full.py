"""E17: delta == full over random single/double-field edits."""

import copy
import json
import os
import random

import pytest

from backend.app.pipeline.pipeline import run_delta
from backend.app.pipeline.pipeline import run_full

MAX_EXAMPLES = int(os.environ.get("E17_MAX_EXAMPLES", "50"))

with open("backend/tests/fixtures/hp1_payload.json") as fh:
    BASE = json.load(fh)

EDITS = [
    ("company.legal_name", ["Acme Trading Co", "Brightline Office Supply", "X"]),
    ("company.trading_name", ["Acme", None]),
    ("company.entity_type", ["LLC", "CORP"]),
    ("tax.tax_id", ["84-1234567", "84-7654321"]),
    ("tax.form_type", ["W9", "W8BEN"]),
    ("tax.tax_classification", ["LLC", "CORP"]),
    ("bank.account_holder_name", ["Brightline Office Supply LLC", "Someone Else"]),
    ("bank.account_number", ["000123456789", "000123456780"]),
    ("bank.routing_number", ["011000015", "011000014"]),
    ("bank.currency", ["USD", "EUR"]),
    ("requester.category", ["OFFICE_SUPPLIES", "IT_SERVICES"]),
    ("requester.data_access", [False, True]),
    ("requester.expected_annual_spend.amount", [18000, 120000, 3000]),
    ("company.primary_contact.email", ["ravi@brightline-office.example", "x@y.co"]),
    ("company.primary_contact.phone", ["+1 614 555 0142", "+1 614 555 0199"]),
    ("declarations.bank_change_justification", [None, "moved banks"]),
]


def _set(payload, path, value):
    node = payload
    parts = path.split(".")
    for p in parts[:-1]:
        node = node[p]
    node[parts[-1]] = value


def _get(payload, path):
    node = payload
    for p in path.split("."):
        node = node[p]
    return node


def _edits(rng):
    n = 1 if rng.random() < 0.7 else 2
    picks = rng.sample(EDITS, n)
    out = []
    for path, values in picks:
        cur = _get(BASE, path)
        choices = [v for v in values if v != cur] or [cur]
        out.append((path, rng.choice(choices)))
    return out


def _strip(result):
    findings = sorted(
        (
            {k: v for k, v in f.items() if k not in ("duration_ms", "cached", "fingerprint")}
            for f in result["findings"]
        ),
        key=lambda f: (f.get("check_id", ""), f.get("subject") or ""),
    )
    for f in findings:
        f["evidence"] = sorted((e.get("kind"), e.get("ref")) for e in f.get("evidence", []))
    dec = {
        k: v
        for k, v in result["decision"].items()
        if k not in ("policy_version", "reproducibility_hash")
    }
    dec["awaiting"] = sorted(dec.get("awaiting", []))
    return {"decision": dec, "findings": findings}


@pytest.mark.parametrize("seed", list(range(MAX_EXAMPLES)))
def test_e17_delta_equals_full(seed):
    rng = random.Random(1000 + seed)
    edited = copy.deepcopy(BASE)
    for path, value in _edits(rng):
        _set(edited, path, value)
    r_full = asyncio_run(run_full(edited))
    r_base = asyncio_run(run_full(BASE))
    r_delta = asyncio_run(
        run_delta(BASE, r_base["findings"], edited, version=2, case_id=r_base["case_id"])
    )
    assert _strip(r_delta) == _strip(r_full), f"seed {seed}"
    assert r_delta["delta"]["cached"] > 0


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
