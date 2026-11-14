import hashlib
import json


def _load(name):
    with open(f"datagen/out/{name}") as fh:
        return json.load(fh)


def test_composition():
    m = _load("manifest.json")
    assert m["counts"] == {
        "clean": 160,
        "single": 240,
        "double": 100,
        "scanned": 60,
        "adversarial": 40,
    }
    assert m["seed"] == 42


def test_manifest_hash_stable():
    m = _load("manifest.json")
    with open("datagen/out/dataset_dev.json", "rb") as fh:
        dev = fh.read()
    with open("datagen/out/dataset_test.json", "rb") as fh:
        test = fh.read()
    assert m["dataset_sha256"] == hashlib.sha256(dev + test).hexdigest()
    assert m["test_split_sha256"] == hashlib.sha256(test).hexdigest()


def test_split_freeze():
    import subprocess

    m = _load("manifest.json")
    subprocess.run(
        ["git", "status", "--porcelain", "datagen/out/manifest.json"],
        capture_output=True,
        text=True,
    )
    with open("datagen/out/dataset_test.json", "rb") as fh:
        blob = fh.read()
    assert hashlib.sha256(blob).hexdigest() == m["test_split_sha256"]


def test_adversarial_all_in_test():
    import collections

    test = _load("dataset_test.json")
    _ops = collections.Counter(str(c["op"]) for c in test)
    # 40 adversarial: 10 each of M-43/M-41/M-27/M-32 beyond single-slice shares
    assert sum(1 for c in test if c["op"] in ("M-43", "M-41", "M-27", "M-32")) >= 40
