"""Coverage: eval mains (replay/off, no live calls) + mini dataset build."""

import json
import sys


def test_run_eval_main_hybrid_limit():
    from eval.run_eval import main

    sys.argv = [
        "run_eval",
        "--split",
        "dev",
        "--mode",
        "hybrid",
        "--limit",
        "2",
        "--out",
        "probe-main.json",
    ]
    main()
    with open("eval/reports/probe-main.json") as fh:
        d = json.load(fh)
    assert d["metrics"]["meta"]["n"] == 2
    import os as _os2

    _os2.remove("eval/reports/probe-main.json")


def test_ablation_run_mode_small():
    from eval.ablation import run_mode

    data = run_mode("-network", "dev", 2, "replay")
    assert data["metrics"]["meta"]["n"] == 2
    data = run_mode("rules-only", "dev", 2, "replay")
    assert data["metrics"]["meta"]["n"] == 2


def test_llm_slice_offline_main(capsys):
    from eval import llm_slice

    llm_slice.main(live=False)
    with open("eval/reports/ablation-llm-only-test25.json") as fh:
        d = json.load(fh)
    assert d["metrics"]["meta"]["n"] >= 20


def test_ablation_main_small():
    import sys

    from eval import ablation

    import glob as _glob

    _bak = {}
    for _f in _glob.glob("eval/reports/*.json") + _glob.glob("eval/reports/*.jsonl"):
        with open(_f, "rb") as _fh:
            _bak[_f] = _fh.read()
    try:
        sys.argv = [
            "ablation",
            "--split",
            "dev",
            "--modes",
            "hybrid,-corroboration",
            "--limit",
            "2",
            "--llm-mode",
            "replay",
        ]
        ablation.main()
        import json as _json

        with open("eval/reports/ablation-dev.json") as fh:
            t = _json.load(fh)
        assert set(t) == {"hybrid", "-corroboration"}
    finally:
        for _f, _blob in _bak.items():
            with open(_f, "wb") as _fh:
                _fh.write(_blob)


def test_llm_only_retry_path(monkeypatch):
    import eval.run_eval as _re

    calls = {"n": 0}

    class _FakeLLM:
        async def structured(self, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("flake")
            from backend.app.llm.tasks_other import LlmOnlyVerdict

            return LlmOnlyVerdict(status="APPROVED", awaiting=[], reason_codes=[], rationale="ok")

    monkeypatch.setattr("backend.app.llm.factory.make_llm", lambda store=None: _FakeLLM())
    import json as _json

    with open("datagen/out/dataset_test.json") as fh:
        case = _json.load(fh)[0]
    pack = _re.llm_only(case, "live")
    assert pack["decision"]["status"] == "APPROVED"
    assert calls["n"] == 3


def test_llm_slice_live_path_fake(monkeypatch):
    import eval.llm_slice as _ls

    def _fake(case, mode):
        from backend.app.llm.tasks_other import LlmOnlyVerdict

        return {
            "decision": LlmOnlyVerdict(
                status="PENDING", awaiting=["VENDOR"], reason_codes=["X"], rationale="fake"
            ).model_dump(),
            "findings": [],
            "run_id": None,
            "_seconds": 0.1,
            "_tokens": 5,
        }

    monkeypatch.setattr(_ls, "llm_only", _fake)
    monkeypatch.setattr(_ls, "FIX", _ls.OUT / "probe-fixtures.json")
    monkeypatch.setattr(_ls, "N", 3)
    _ls.main(live=True)
    import json as _json
    import os as _os

    with open("eval/reports/probe-fixtures.json") as _fh:
        assert _json.load(_fh)
    _os.remove("eval/reports/probe-fixtures.json")


def test_mini_dataset_build():
    import random

    import datagen.build_dataset as B

    rng = random.Random(9)
    with open("datagen/out/world.json") as fh:
        world = json.load(fh)
    vendors = [v for v in world["vendors"] if "-B" not in v["vendor_id"]][:4]
    cases = [("clean", B._clean(v, world, rng)) for v in vendors]
    cases.append(("single", B._op_case("M-06", world, rng)))
    cases.append(("double", B._double_case("M-45", "M-39", world, rng)))
    assert all(c[1]["expected"]["status"] for c in cases)
    assert all("files" in c[1] and "l3" in c[1] for c in cases)
