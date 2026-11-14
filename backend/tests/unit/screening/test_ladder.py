from backend.app.screening import sanctions as san


def _entry(name, country="", year=0, reg=""):
    return {
        "id": "T",
        "type": "entity",
        "names": [name],
        "aliases": [],
        "country": country,
        "reg_no": reg,
        "incorporation_year": year,
        "addresses": [],
        "program": "T",
    }


def test_confirmed_needs_secondary():
    r = san.screen(
        "Meridian Shipping Svcs LLC",
        {"country": "PA", "incorporation_year": 2009, "reg_no": ""},
        [_entry("Meridian Shipping Svcs LLC", "PA", 2009)],
    )
    assert r["verdict"] == "CONFIRMED"


def test_cleared_needs_two_contradictions():
    r = san.screen(
        "Meridian Shipping Svcs LLC",
        {"country": "GB", "incorporation_year": 2021, "reg_no": ""},
        [_entry("Meridian Shipping Svcs LLC", "PA", 2009)],
    )
    assert r["verdict"] == "CLEARED_RATIONALE"


def test_potential_without_secondary():
    r = san.screen(
        "Meridian Shipping Svcs LLC",
        {"country": "", "incorporation_year": 0, "reg_no": ""},
        [_entry("Meridian Shipping Svcs LLC", "PA", 2009)],
    )
    assert r["verdict"] == "POTENTIAL"


def test_no_match_below_threshold():
    r = san.screen(
        "Completely Different Name Ltd",
        {"country": "GB", "incorporation_year": 2020, "reg_no": ""},
        [_entry("Meridian Shipping Svcs LLC", "PA", 2009)],
    )
    assert r["verdict"] == "NO_MATCH"


def test_no_llm_in_screening_path():
    import pathlib

    src = pathlib.Path("backend/app/pipeline/checks/san.py").read_text()
    assert "llm" not in src
    src2 = pathlib.Path("backend/app/screening/sanctions.py").read_text()
    assert "llm" not in src2


def test_screening_edge_branches():
    import backend.app.screening.sanctions as m

    assert m._load("nonexistent.jsonl") == []
    assert m._aliases({"names": []}) == [""]
    r = san.screen("X", {"country": "", "incorporation_year": 0, "reg_no": ""}, [])
    assert r["verdict"] == "NO_MATCH"
