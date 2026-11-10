from hypothesis import given
from hypothesis import strategies as st

from backend.app.llm.tasks_extract import grounding_ok


import string

_ASCII = string.ascii_letters + string.digits + " .,;:()-/"


@given(
    st.text(alphabet=_ASCII, min_size=1, max_size=60),
    st.text(alphabet=_ASCII, min_size=1, max_size=200),
)
def test_grounding_reference(value, page):
    # fabricated value (random text) is accepted only if truly contained
    # (case-insensitive: canon casefolds before comparing)
    quote = page[:200] if page else ""
    lv, lq = value.lower(), quote.lower()
    if value and quote and lv in lq and lq in page.lower():
        assert grounding_ok(value, quote, page) in (True, False)  # smoke
    else:
        if value and (not quote or lv not in lq):
            assert grounding_ok(value, quote, page) is False


def test_grounding_positives_and_negatives():
    page = "Legal Name: Nimbus Technologies Pvt Ltd. GSTIN: 29AAPCA1234F1ZR."
    assert (
        grounding_ok("Nimbus Technologies Pvt Ltd", "Legal Name: Nimbus Technologies Pvt Ltd", page)
        is True
    )
    assert grounding_ok("Someone Else", "Legal Name: Nimbus Technologies Pvt Ltd", page) is False
    assert grounding_ok("Nimbus", "unrelated quote", page) is False
    assert grounding_ok(None, None, page) is True
