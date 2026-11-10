"""Gap coverage for the 90% gate on validators/matching/risk."""

import pytest

from backend.app.matching import legal_forms
from backend.app.matching.similarity import is_initialism
from backend.app.matching.similarity import ngram_jaccard
from backend.app.validators.iban import validate_iban
from backend.app.validators.iban import validate_swift
from backend.app.validators.phone import validate_phone


def test_legal_forms_canonical():
    forms = legal_forms.load_forms()
    assert legal_forms.canonical_form("pvt ltd", forms) == "LTD_PRIVATE_IN"
    assert legal_forms.canonical_form("nonsense xyz", forms) is None
    core, form = legal_forms.strip_form_suffix("Acme", forms)
    assert core == "Acme" and form is None
    assert legal_forms.compare_forms(None, None) == "COMPATIBLE"
    assert legal_forms.compare_forms("CO", "CO") == "SAME"


def test_similarity_edges():
    assert ngram_jaccard("", "") == 1.0
    assert ngram_jaccard("abc", "") == 0.0
    assert is_initialism("IBM", "International Business Machines") is True
    assert is_initialism("Acme Trading", "Beta Corp") is False


def test_iban_swift_edges():
    from backend.app.validators.iban import iban_valid

    assert iban_valid("AB") is False
    assert iban_valid("DE89-370400440532013000") is False
    assert validate_iban("XX").reason == "BAD_STRUCTURE"
    assert validate_iban("ZZ12345678901234567890").reason == "WRONG_COUNTRY_SHAPE"
    assert validate_swift("SHORT").reason == "BAD_LENGTH"
    assert validate_swift("12345678").reason == "BAD_CHARSET"
    assert validate_iban("DE89 3704 0044 0532 0130 00").valid


def test_phone_edges():
    assert validate_phone("!!!", "US").reason == "BAD_STRUCTURE"
    assert validate_phone("+1 000 000 0000", "US").reason in ("BAD_STRUCTURE", None)


def test_alias_modules_importable():
    import backend.app.validators.aba as aba
    import backend.app.validators.ifsc as ifsc
    import backend.app.validators.pan as pan
    import backend.app.validators.postal as postal
    import backend.app.validators.swift as swift

    assert aba.validate_aba("011000015").valid
    assert ifsc.validate_ifsc("HDFC0001234").valid
    assert pan.validate_pan("AAAPC1234F").valid
    assert postal.validate_postal("43215", "US").valid
    assert swift.validate_swift("DEUTDEFF").valid


def test_components_branches():
    from backend.app.risk import components

    class _Ctx:
        def __init__(self, values, policy):
            self._v = values
            self.policy = policy

        def value(self, path):
            return self._v.get(path)

    from backend.app.core.policy import load_policy

    p = load_policy("policy")
    one_time = _Ctx(
        {
            "requester.expected_annual_spend_usd": 30000,
            "requester.one_time": "True",
            "requester.category": "OFFICE_SUPPLIES",
            "requester.data_access": "False",
            "company.country": "US",
            "bank.country": "GB",
        },
        p,
    )
    raw, _ = components.component_spend(one_time, {})
    assert raw == 0.6  # 30k band 0.5 + one_time 0.1
    raw, _ = components.component_geo(one_time, {"GEO": 0.2})
    assert raw > 0.3
    da = _Ctx(
        {
            "requester.expected_annual_spend_usd": 1000,
            "requester.one_time": "False",
            "requester.category": "IT_SERVICES",
            "requester.data_access": "True",
            "company.country": "US",
            "bank.country": "US",
        },
        p,
    )
    raw, _ = components.component_category(da, {})
    assert raw == pytest.approx(0.9)
    raw, _ = components.component_registry_media(da, {"REGISTRY_MEDIA": 0.4})
    assert raw == 0.4
