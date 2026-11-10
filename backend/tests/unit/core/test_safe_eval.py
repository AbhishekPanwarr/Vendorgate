import pytest

from backend.app.core.safe_eval import PolicyExpressionError
from backend.app.core.safe_eval import safe_eval


def test_whitelist():
    assert safe_eval("a == 'x'", {"a": "x"}) is True
    assert safe_eval("a in ['x','y'] and b > 1", {"a": "x", "b": 2}) is True
    assert safe_eval("not (a != 'x')", {"a": "x"}) is True
    assert safe_eval("d['k'] == 1", {"d": {"k": 1}}) is True


def test_rejects():
    with pytest.raises(PolicyExpressionError):
        safe_eval("__import__('os').system('x')", {})
    with pytest.raises(PolicyExpressionError):
        safe_eval("(lambda: 1)()", {})
    with pytest.raises(PolicyExpressionError):
        safe_eval("[x for x in y]", {"x": 1, "y": [1]})
    with pytest.raises(PolicyExpressionError):
        safe_eval("obj.__class__", {"obj": 1})
    with pytest.raises(PolicyExpressionError):
        safe_eval("open('f')", {})
    with pytest.raises(PolicyExpressionError):
        safe_eval("a.attr", {"a": 1})
    with pytest.raises(PolicyExpressionError):
        safe_eval("a[b]", {"c": 1})
