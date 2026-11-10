from hypothesis import given
from hypothesis import strategies as st

from backend.app.matching.normalize import canon_id
from backend.app.matching.normalize import canon_text


@given(st.text(max_size=40))
def test_idempotent_and_ws_invariant(s):
    a, _ = canon_text(s)
    b, _ = canon_text(a)
    assert a == b
    c, _ = canon_text("  " + s + "  ")
    d, _ = canon_text(s.strip())
    assert c == d


@given(st.text(min_size=1, max_size=20))
def test_canon_id_stable(s):
    assert canon_id(s) == canon_id(canon_id(s))
