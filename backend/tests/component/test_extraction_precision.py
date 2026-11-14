"""E11: grounding precision on the L1 cache (live + hand-authored)."""

import json
from pathlib import Path

from backend.app.llm.tasks_extract import grounding_ok


def test_grounding_precision():
    store = {}
    for path in sorted(Path("backend/tests/fixtures/llm_cache").glob("*.json")):
        store.update(json.loads(path.read_text()))
    checked = correct = 0
    for key, entry in store.items():
        if not isinstance(entry, dict) or "_tokens_used" not in entry:
            continue
        # only L1 extraction entries (have Field-shaped values)
        fields = {k: v for k, v in entry.items() if isinstance(v, dict) and "quote" in v}
        if not fields:
            continue
        for name, f in fields.items():
            if f.get("value") is None:
                continue
            checked += 1
            # quote must be non-empty and contain the value (grounded by construction)
            if f.get("quote") and str(f["value"]) in str(f["quote"]):
                correct += 1
    precision = correct / checked if checked else 1.0
    print(f"\nE11: {correct}/{checked} = {precision:.3f}")
    assert checked >= 20
    assert precision >= 0.99


def test_live_recorded_grounded_against_pdfs():
    from backend.app.ingest.text import extract_text_layer

    pdf_for = {"gst_hp2": "gst_hp2.pdf", "bank_hp1": "bank_hp1.pdf"}
    texts = {}
    for key, fn in pdf_for.items():
        with open(f"backend/tests/fixtures/pdfs/{fn}", "rb") as fh:
            pages, _ = extract_text_layer(fh.read())
        texts[key] = "\n".join(pages)
    store = json.loads(Path("backend/tests/fixtures/llm_cache/recorded_live.json").read_text())
    n = 0
    for entry in store.values():
        for name, f in entry.items():
            if not isinstance(f, dict) or f.get("value") is None:
                continue
            n += 1
            assert grounding_ok(
                f["value"], f["quote"], texts["gst_hp2"] + "\n" + texts["bank_hp1"]
            ), name
    assert n >= 8
