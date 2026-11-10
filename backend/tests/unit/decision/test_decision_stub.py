from backend.app.decision import engine


def test_apply_resolutions_passthrough():
    assert engine.apply_resolutions([], []) == []


def test_counterfactuals_standalone_raises():
    import pytest

    with pytest.raises(NotImplementedError):
        engine.counterfactuals()


def test_decide_implemented():
    from backend.app.core.policy import load_policy
    from backend.app.domain.models import RiskBreakdown

    assert load_policy("policy").version
    assert RiskBreakdown is not None
