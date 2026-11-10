import asyncio
import json

from backend.app.adapters.faults import clear_faults
from backend.app.adapters.faults import set_fault
from backend.app.pipeline.pipeline import run_full


def _hp1():
    with open("backend/tests/fixtures/hp1_payload.json") as fh:
        return json.load(fh)


def test_each_adapter_outage_blocks_approval():
    for adapter in ("irs", "bank"):
        set_fault(adapter, "TIMEOUT")
        try:
            r = asyncio.run(run_full(_hp1()))
            d = r["decision"]
            assert d["status"] == "PENDING", adapter
            assert d["awaiting"] == ["INTERNAL"], adapter
            assert any(f.get("reason_code") == "VERIFIER_UNAVAILABLE" for f in r["findings"]), (
                adapter
            )
        finally:
            clear_faults()


def test_restore_and_rerun_approves():
    set_fault("irs", "TIMEOUT")
    try:
        r = asyncio.run(run_full(_hp1()))
        assert r["decision"]["status"] == "PENDING"
    finally:
        clear_faults()
    r2 = asyncio.run(run_full(_hp1()))
    assert r2["decision"]["status"] == "APPROVED"


def test_never_approved_while_unverifiable():
    set_fault("bank", "ERROR")
    try:
        r = asyncio.run(run_full(_hp1()))
        assert r["decision"]["status"] != "APPROVED"
    finally:
        clear_faults()
