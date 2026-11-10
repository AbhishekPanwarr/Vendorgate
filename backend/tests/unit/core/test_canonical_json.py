from backend.app.core.hashing import canonical_json
from backend.app.core.hashing import fingerprint


def test_key_order_irrelevant():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})
    assert " " not in canonical_json({"a": 1})


def test_unicode_nfc():
    assert canonical_json("é") == canonical_json("é")


def test_fingerprint_stability():
    kw = dict(
        check_id="C-X",
        version=1,
        subject=None,
        policy_hash="p",
        reads={"a": 1},
        adapters={},
        lists={},
    )
    assert fingerprint(**kw) == fingerprint(**kw)


def test_fingerprint_read_change():
    kw = dict(check_id="C-X", version=1, subject=None, policy_hash="p", adapters={}, lists={})
    assert fingerprint(reads={"a": 1}, **kw) != fingerprint(reads={"a": 2}, **kw)


def test_fingerprint_key_order():
    kw = dict(check_id="C-X", version=1, subject=None, policy_hash="p", adapters={}, lists={})
    assert fingerprint(reads={"a": 1, "b": 2}, **kw) == fingerprint(reads={"b": 2, "a": 1}, **kw)
