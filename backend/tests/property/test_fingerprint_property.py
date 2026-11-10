from hypothesis import given
from hypothesis import strategies as st

from backend.app.core.hashing import fingerprint


@given(st.dictionaries(st.text(min_size=1, max_size=4), st.integers(), max_size=4))
def test_perm_keys(reads):
    kw = dict(check_id="C", version=1, subject=None, policy_hash="p", adapters={}, lists={})
    a = fingerprint(reads=dict(reads), **kw)
    b = fingerprint(reads=dict(reversed(list(reads.items()))), **kw)
    assert a == b


@given(st.dictionaries(st.text(min_size=1, max_size=4), st.integers(), max_size=4))
def test_mutation_changes(reads):
    kw = dict(check_id="C", version=1, subject=None, policy_hash="p", adapters={}, lists={})
    if not reads:
        return
    k = next(iter(reads))
    alt = dict(reads)
    alt[k] = alt[k] + 1
    assert fingerprint(reads=reads, **kw) != fingerprint(reads=alt, **kw)
