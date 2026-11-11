"""E11/E12/E14 from the dedicated test sets."""

import binascii
import json
from pathlib import Path

OUT = Path("eval/reports")


def name_pairs() -> dict:
    from backend.app.core.policy import load_policy
    from backend.app.matching.name_compare import compare_names, parse_name

    cfg = dict(load_policy("policy").raw["base"]["matching"]["name"])
    rows = []
    for name in ("true_variants.jsonl", "hard_negatives.jsonl"):
        with open(f"datagen/name_pairs/{name}") as fh:
            for line in fh:
                rows.append(json.loads(line))
    tp = fp = tn = fn = 0
    false_merge = 0
    n_diff = 0
    n_same_recall = 0
    n_same = 0
    for r in rows:
        rel = compare_names(parse_name(r["a"].lower()),
                            parse_name(r["b"].lower()), cfg).relation
        merged = rel in ("EXACT", "EQUIVALENT")
        if r["label"] == "SAME":
            n_same += 1
            n_same_recall += 1 if rel != "DIFFERENT" else 0
            tp += 1 if merged else 0
            fn += 0 if merged else 1
        else:
            n_diff += 1
            false_merge += 1 if merged else 0
            tn += 0 if merged else 1
            fp += 1 if merged else 0
    from eval.metrics import rate

    return {"E12": {"false_merge": rate(false_merge, n_diff),
                    "recall": rate(n_same_recall, n_same),
                    "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}}}


def extraction() -> dict:
    from eval.metrics import rate

    with open("datagen/extraction_set/ground_truth.json") as fh:
        gt = json.load(fh)
    from backend.app.ingest import extract_regex
    from backend.app.ingest.text import extract_text_layer, ocr_pdf_bytes

    text_hits = text_n = scan_hits = scan_n = 0
    ground_hits = ground_n = 0
    sgn, sgh, tgn, tgh = [0], [0], [0], [0]
    for g in gt:
        raw = (Path("datagen/extraction_set")
               / ("scanned" if g["scanned"] else "text_layer")
               / f"{g['id']}.pdf").read_bytes()
        pages, layered = extract_text_layer(raw)
        if not layered:
            try:
                pages, _ = ocr_pdf_bytes(raw)
            except Exception:
                pages = []
        text = "\n".join(pages)
        found = extract_regex.extract(text)
        fields = {"W9": ["tin"], "GST_CERT": ["gstin"], "VAT_CERT": ["vat_id"],
                  "BANK_LETTER": ["account_number", "letter_date"],
                  "COI": ["expiry_date"], "INCORP_CERT": []}
        # names/holders are L1-covered, not regex-covered; INCORP has no
        # regex-covered fields (tracked in Limitations, not in the rate)
        keys = fields.get(g["doc_type"], [])
        for k in keys:
            want = str(g["truth"].get({
                "tin": "tin", "gstin": "gstin", "vat_id": "vat_id",
                "account_number": "account_number", "letter_date": "letter_date",
                "expiry_date": "expiry_date"}[k], ""))
            if not want:
                continue
            hit = any(want in (v or "") for vals in found.values()
                      for v, _q in vals[:3])
            if g["scanned"]:
                scan_n += 1
                scan_hits += 1 if hit else 0
            else:
                text_n += 1
                text_hits += 1 if hit else 0
        # grounding: every truth value verbatim in extracted text
        for kk, vv in g["truth"].items():
            if not vv or not isinstance(vv, str):
                continue
            ground_n += 1
            ground_hits += 1 if vv in text else 0
            if g["scanned"]:
                sgn[0] += 1
                sgh[0] += 1 if vv in text else 0
            else:
                tgn[0] += 1
                tgh[0] += 1 if vv in text else 0
    return {"E11": {"text": rate(text_hits, text_n),
                    "scanned": rate(scan_hits, scan_n),
                    "grounding": rate(ground_hits, ground_n),
                    "grounding_text": rate(tgh[0], tgn[0]),
                    "grounding_scanned": rate(sgh[0], sgn[0])}}


def network() -> dict:
    from eval.metrics import rate

    with open("datagen/network_set/clusters.json") as fh:
        clusters = json.load(fh)
    with open("datagen/out/world.json") as fh:
        world = json.load(fh)
    from backend.app.matching.normalize import canon_text
    from backend.app.network import graph

    graph._EXTRA_VENDORS.clear()
    for cl in clusters:
        for m in cl["members"]:
            core, _ = canon_text(m["legal_name"])
            graph._EXTRA_VENDORS[m["vendor_id"]] = {
                "vendor_id": m["vendor_id"], "legal_name": m["legal_name"],
                "name_core": core, "tax_id": "X",
                "bank": graph.bank_key("US", "0", m["bank"].get("account_number", "")),
                "phone": m["phone"]}
    detected = 0
    for cl in clusters:
        anchor = cl["members"][0]
        hits = graph.find_bank_reuse(
            graph.bank_key("US", "0", anchor["bank"].get("account_number", "")))
        ids = {h["vendor_id"] for h in hits}
        if {m["vendor_id"] for m in cl["members"]} <= ids:
            detected += 1
    # precision proxy: random outsiders should not match cluster banks
    outsiders = [v for v in world["vendors"]
                 if v["vendor_id"] not in graph._EXTRA_VENDORS][:30]
    fp = 0
    for v in outsiders:
        hits = graph.find_bank_reuse(
            graph.bank_key(v["country"], "0",
                           v["bank"].get("account_number", "")))
        if hits:
            fp += 1
    graph._EXTRA_VENDORS.clear()
    return {"E14": {"recall": rate(detected, len(clusters)),
                    "precision_proxy": rate(len(outsiders) - fp, len(outsiders))}}


def main() -> None:
    out = {}
    out.update(name_pairs())
    out.update(extraction())
    out.update(network())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sets.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: {m: v[m] for m in v} for k, v in out.items()
                      for m in [next(iter(v))]}, indent=1)[:800])
    print("wrote eval/reports/sets.json")


if __name__ == "__main__":
    main()
