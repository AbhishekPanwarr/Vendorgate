"""Golden snapshots: full pipeline replay vs committed fixtures."""

import asyncio
import json

import pytest

from backend.app.pipeline.pipeline import run_full

NAMES = [
    "hp-1",
    "hp-2",
    "hp-3",
    "hp-3-high",
    "ec-1-run-1",
    "ec-2a",
    "ec-2b",
    "ec-2c",
    "ec-3a",
    "ec-3b",
    "ec-4a",
    "ec-4b",
    "ec-4d-outage",
    "ec-18",
]


def strip_volatile(result: dict) -> dict:
    out = {"decision": result["decision"], "findings": []}
    for f in result["findings"]:
        g = {k: v for k, v in f.items() if k not in ("duration_ms", "cached", "fingerprint")}
        # call_ids/fixture runs vary per execution; keep shape only
        g["evidence"] = sorted((e.get("kind"), e.get("ref")) for e in f.get("evidence", []))
        out["findings"].append(g)
    out["decision"] = {
        k: v
        for k, v in result["decision"].items()
        if k not in ("policy_version", "reproducibility_hash")
    }
    out["decision"]["awaiting"] = sorted(out["decision"].get("awaiting", []))
    out["decision"]["reason_codes"] = sorted(out["decision"].get("reason_codes", []))
    out["decision"]["blocking_finding_ids"] = sorted(
        out["decision"].get("blocking_finding_ids", [])
    )
    return out


def strip_fixture(fx: dict) -> dict:
    return strip_volatile({"decision": fx["decision"], "findings": fx["findings"]})


@pytest.mark.parametrize("name", NAMES)
def test_golden(name, request):
    from backend.app.adapters.faults import clear_faults, set_fault

    with open(f"backend/tests/golden/fixtures/{name}.json") as fh:
        fx = json.load(fh)
    if name == "ec-4d-outage":
        set_fault("registry", "TIMEOUT")  # documented precondition for this golden
    try:
        result = asyncio.run(run_full(fx["payload"]))
    finally:
        clear_faults()
    if request.config.getoption("--update-goldens"):
        with open(f"backend/tests/golden/fixtures/{name}.json", "w") as fh:
            json.dump(
                {
                    "payload": fx["payload"],
                    "decision": result["decision"],
                    "findings": result["findings"],
                },
                fh,
                indent=1,
            )
        pytest.skip("golden regenerated (review diff before commit)")
    assert strip_volatile(result) == strip_fixture(fx)
