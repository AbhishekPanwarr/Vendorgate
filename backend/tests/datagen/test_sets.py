import json as _json


def _loadl(path):
    with open(path) as _fh:
        return [_json.loads(line) for line in _fh]


def _loadj(path):
    with open(path) as _fh:
        return _json.load(_fh)


def test_name_pairs():
    from backend.app.core.policy import load_policy
    from backend.app.matching.name_compare import compare_names, parse_name
    from eval.metrics import rate

    cfg = dict(load_policy("policy").raw["base"]["matching"]["name"])
    same = _loadl("datagen/name_pairs/true_variants.jsonl")
    diff = _loadl("datagen/name_pairs/hard_negatives.jsonl")
    assert len(same) == 150 and len(diff) == 150
    fm = sum(1 for r in diff
             if compare_names(parse_name(r["a"].lower()),
                              parse_name(r["b"].lower()), cfg).relation
             in ("EXACT", "EQUIVALENT"))
    assert rate(fm, len(diff))["rate"] <= 0.005
    rec = sum(1 for r in same
              if compare_names(parse_name(r["a"].lower()),
                               parse_name(r["b"].lower()), cfg).relation != "DIFFERENT")
    assert rate(rec, len(same))["rate"] >= 0.95


def test_ambiguous_template():
    rows = _loadl("datagen/name_pairs/ambiguous.jsonl")
    assert len(rows) == 100
    assert all(r["label"] is None for r in rows)  # hand-labels pending (user session)


def test_extraction_set():
    gt = _loadj("datagen/extraction_set/ground_truth.json")
    assert len(gt) == 120
    assert sum(1 for g in gt if g["scanned"]) == 60
    assert sum(1 for g in gt if not g["scanned"]) == 60


def test_network_set():
    clusters = _loadj("datagen/network_set/clusters.json")
    assert len(clusters) == 15
    assert all(2 <= len(c["members"]) <= 4 for c in clusters)
