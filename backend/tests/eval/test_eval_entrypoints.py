"""Eval entry points at import level (no live LLM calls)."""

import json


def test_sets_eval_functions():
    from eval.sets_eval import extraction, name_pairs, network

    np_ = name_pairs()
    assert np_["E12"]["false_merge"]["k"] == 0
    net = network()
    assert net["E14"]["recall"]["k"] == 15
    ex = extraction()
    assert ex["E11"]["text"]["rate"] >= 0.9


def test_llm_slice_offline():
    from eval.llm_slice import case_key, sample

    with open("datagen/out/dataset_test.json") as fh:
        test = json.load(fh)
    picks = sample(test)
    assert 20 <= len(picks) <= 25
    # duplicate payloads share a key by design (identical cases)
    assert len({case_key(c) for c in picks}) <= len(picks)


def test_ablation_table_shape():
    with open("eval/reports/ablation-dev.json") as fh:
        t = json.load(fh)
    assert set(t) >= {
        "hybrid",
        "rules-only",
        "corroboration",
        "fail-closed",
        "network",
        "counterfactual",
    }
    for m, row in t.items():
        assert {"E1", "E3", "E5", "E6_f1", "p95"} <= set(row)
