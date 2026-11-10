import pytest

from backend.app.pipeline import registry


def test_register_and_lookup():
    registry.clear()

    @registry.check(id="C-T1", stage="S3", version=1, reads=("a",))
    async def _fn(ctx):  # noqa: ANN001, ANN202
        return []

    assert registry.get("C-T1").reads == ("a",)
    assert registry.specs_by_stage("S3")[0].id == "C-T1"
    registry.clear()


def test_duplicate_raises():
    registry.clear()

    @registry.check(id="C-D", stage="S3", version=1)
    async def _a(ctx):  # noqa: ANN001, ANN202
        return []

    with pytest.raises(ValueError):

        @registry.check(id="C-D", stage="S3", version=1)
        async def _b(ctx):  # noqa: ANN001, ANN202
            return []

    registry.clear()


def test_invalid_stage_raises():
    registry.clear()
    with pytest.raises(ValueError):

        @registry.check(id="C-Z", stage="SX", version=1)
        async def _z(ctx):  # noqa: ANN001, ANN202
            return []

    registry.clear()
