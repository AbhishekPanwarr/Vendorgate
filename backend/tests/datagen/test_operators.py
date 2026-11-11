"""Each mutation operator: apply -> run engine -> outcome matches catalog."""

import json

import pytest
import yaml

from eval.case_runner import run_case

with open("datagen/mutations/catalog.yaml") as fh:
    CATALOG = {o["id"]: o for o in yaml.safe_load(fh)["operators"]}
with open("datagen/out/world.json") as fh:
    WORLD = json.load(fh)

OPS = sorted(CATALOG.keys())


def _one(op_id, seed=7):
    import random

    from datagen.build_dataset import COUNTRY_OF, _pick, build_case

    rng = random.Random(seed)
    vendor = _pick(WORLD, rng, COUNTRY_OF.get(op_id))
    return build_case(op_id, vendor, WORLD, rng)


@pytest.mark.parametrize("op_id", OPS)
def test_operator_matches_expected(op_id):
    case = _one(op_id)
    pack = run_case(case)
    dec = pack["decision"]
    exp = CATALOG[op_id]["expected"]
    assert dec["status"] == exp["status"], (
        f"{op_id}: status {dec['status']} != {exp['status']}; "
        f"awaiting={dec['awaiting']} codes={dec['reason_codes']}"
    )
    assert sorted(dec["awaiting"]) == sorted(exp["awaiting"]), op_id
    # recall: every expected code must fire; extra codes are defense-in-depth
    # (measured separately as E6 exact-set) and must not change status/awaiting
    assert set(exp["blocking_reason_codes"]) <= set(dec["reason_codes"]), (
        f"{op_id}: missing {set(exp['blocking_reason_codes']) - set(dec['reason_codes'])} "
        f"in {dec['reason_codes']}"
    )


def test_control_operators_approve():
    import random

    from datagen.build_dataset import COUNTRY_OF, _pick, build_case

    for op_id in ("M-08", "M-10", "M-14", "M-31", "M-39", "M-44", "M-45"):
        rng = random.Random(11)
        case = build_case(op_id, _pick(WORLD, rng, COUNTRY_OF.get(op_id)), WORLD, rng)
        pack = run_case(case)
        assert pack["decision"]["status"] == "APPROVED", (
            f"{op_id}: {pack['decision']['status']} {pack['decision']['reason_codes']}"
        )
    # M-11 is vendor-sensitive by construction; sweep 5 vendors
    for seed in range(5):
        rng = random.Random(100 + seed)
        case = build_case("M-11", _pick(WORLD, rng, COUNTRY_OF.get("M-11")), WORLD, rng)
        pack = run_case(case)
        assert pack["decision"]["status"] == "APPROVED", (
            f"M-11 seed {seed}: {pack['decision']['status']} {pack['decision']['reason_codes']}"
        )
