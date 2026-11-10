from hypothesis import given
from hypothesis import strategies as st

from backend.app.core.hashing import canonical_json


@given(st.dictionaries(st.text(max_size=5), st.integers(), max_size=5))
def test_perm_order(d):
    items = list(d.items())
    assert canonical_json(dict(items)) == canonical_json(dict(reversed(items)))


@given(st.text())
def test_nfc(s):
    import unicodedata

    assert canonical_json(s) == canonical_json(unicodedata.normalize("NFC", s))
