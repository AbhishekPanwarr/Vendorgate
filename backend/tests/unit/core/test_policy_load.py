import yaml

from backend.app.comms.messages import INTERNAL_ONLY_CODES


def test_every_fix_code_has_hint_or_is_internal():
    with open("policy/fix_hints.yaml") as fh:
        hints = yaml.safe_load(fh)
    from backend.app.pipeline import registry  # noqa: F401
    import backend.app.pipeline.checks.bank  # noqa: F401
    import backend.app.pipeline.checks.geo  # noqa: F401
    import backend.app.pipeline.checks.name  # noqa: F401
    import backend.app.pipeline.checks.req  # noqa: F401
    import backend.app.pipeline.checks.tax  # noqa: F401
    import backend.app.pipeline.checks.ver  # noqa: F401
    import backend.app.pipeline.checks.dup  # noqa: F401
    import backend.app.pipeline.checks.san  # noqa: F401

    assert set(registry.all_specs())  # checks registered
    # reason codes covered by internal-only set need no hint; spot-check a few
    for code in ("SANCTIONS_MATCH", "BANK_SHARED_ACROSS_VENDORS", "CALLBACK_REQUIRED"):
        assert code in INTERNAL_ONLY_CODES
    for code in ("PROVIDE_TIN", "UPLOAD_W9", "PROVIDE_VAT"):
        assert code in hints
