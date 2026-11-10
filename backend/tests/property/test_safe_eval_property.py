import pytest
from hypothesis import given
from hypothesis import strategies as st

from backend.app.core.safe_eval import PolicyExpressionError
from backend.app.core.safe_eval import safe_eval


@given(
    st.sampled_from(
        [
            ("a == 'x'", {"a": "x"}),
            ("b in [1,2]", {"b": 1}),
            ("not c", {"c": False}),
            ("a > 1", {"a": 2}),
        ]
    )
)
def test_valid(case):
    expr, ctx = case
    assert safe_eval(expr, ctx) in (True, False)


@given(
    st.sampled_from(
        ["f(x)", "a.b", "import os", "(lambda: 1)()", "{'a':1}", "{1,2}", "[x for x in y]"]
    )
)
def test_invalid(expr):
    with pytest.raises(PolicyExpressionError):
        safe_eval(expr, {"a": 1, "x": 1, "y": [1], "b": 1, "f": 1})
