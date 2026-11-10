import pytest

from backend.app.decision import engine


def test_decide_stub():
    with pytest.raises(NotImplementedError, match="Phase 1"):
        engine.decide(findings=[], resolutions=[], submission_facts={}, policy={})


def test_apply_stub():
    with pytest.raises(NotImplementedError, match="Phase 1"):
        engine.apply_resolutions([], [])


def test_counterfactual_stub():
    with pytest.raises(NotImplementedError, match="Phase 1"):
        engine.counterfactuals()
