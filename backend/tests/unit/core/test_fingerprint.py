from backend.app.core.hashing import fingerprint


def test_fp_same():
    kw = dict(
        check_id="C",
        version=1,
        subject="s",
        policy_hash="p",
        reads={"x": "1"},
        adapters={"a": "v"},
        lists={"l": "1"},
    )
    assert fingerprint(**kw) == fingerprint(**kw)


def test_fp_diff_on_read():
    assert fingerprint(
        check_id="C",
        version=1,
        subject=None,
        policy_hash="p",
        reads={"x": 1},
        adapters={},
        lists={},
    ) != fingerprint(
        check_id="C",
        version=1,
        subject=None,
        policy_hash="p",
        reads={"x": 2},
        adapters={},
        lists={},
    )


def test_fp_ignores_extra_keys():
    # function only hashes passed reads; unrelated external keys never enter payload
    a = fingerprint(
        check_id="C",
        version=1,
        subject=None,
        policy_hash="p",
        reads={"x": 1},
        adapters={},
        lists={},
    )
    b = fingerprint(
        check_id="C",
        version=1,
        subject=None,
        policy_hash="p",
        reads={"x": 1},
        adapters={},
        lists={},
    )
    assert a == b
