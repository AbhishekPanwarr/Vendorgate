import json

from backend.app.core.policy import load_policy
from backend.app.matching.name_compare import compare_names
from backend.app.matching.name_compare import parse_name

CFG = load_policy("policy").raw["base"]["matching"]["name"]


def test_ec1_pair_is_form_conflict():
    c = compare_names(parse_name("Acme Trading Co"), parse_name("ACME TRADING COMPANY LLC"), CFG)
    assert c.relation == "FORM_CONFLICT"


def test_abbreviation_equivalent():
    c = compare_names(
        parse_name("Intl Business Machines"), parse_name("International Business Machines"), CFG
    )
    assert c.relation in ("EQUIVALENT", "EXACT")


def test_strict_subset_never_exact():
    c = compare_names(parse_name("Acme"), parse_name("Acme Holdings"), CFG)
    assert c.relation in ("CORE_FUZZY", "DIFFERENT")


def test_thresholds_read_from_policy():
    default = compare_names(parse_name("Acme"), parse_name("Acme Holdings"), CFG)
    assert default.relation == "DIFFERENT"
    loose = dict(CFG, t_hi=0.50)
    c = compare_names(parse_name("Acme"), parse_name("Acme Holdings"), loose)
    assert c.relation in ("EQUIVALENT", "FORM_CONFLICT", "CORE_FUZZY")


def test_dev_set_sanity():
    with open("backend/tests/fixtures/name_pairs_dev.json") as fh:
        pairs = json.load(fh)["pairs"]
    assert len(pairs) == 50
    variants = [p for p in pairs if p["label"] == "variant"]
    negatives = [p for p in pairs if p["label"] == "negative"]
    missed = [
        p
        for p in variants
        if compare_names(parse_name(p["a"]), parse_name(p["b"]), CFG).relation == "DIFFERENT"
    ]
    merged = [
        p
        for p in negatives
        if compare_names(parse_name(p["a"]), parse_name(p["b"]), CFG).relation
        in ("EXACT", "EQUIVALENT")
    ]
    recall = (len(variants) - len(missed)) / len(variants)
    print(
        f"\ndev sanity: recall {recall:.2f} ({len(missed)} missed), false-merge {len(merged)}/{len(negatives)}"
    )
    assert recall >= 0.90
    assert len(merged) <= 1
