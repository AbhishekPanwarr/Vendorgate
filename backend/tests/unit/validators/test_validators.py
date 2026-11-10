from backend.app.validators.ein import aba_valid
from backend.app.validators.ein import validate_aba
from backend.app.validators.ein import validate_ein
from backend.app.validators.gstin import validate_gstin
from backend.app.validators.gstin import validate_ifsc
from backend.app.validators.gstin import validate_pan
from backend.app.validators.iban import validate_iban
from backend.app.validators.iban import validate_swift
from backend.app.validators.phone import validate_phone
from backend.app.validators.phone import validate_postal
from backend.app.validators.vat import validate_de_vat
from backend.app.validators.vat import validate_gb_vat


def test_gstin_anchor():
    r = validate_gstin("27AAPFU0939F1ZV")
    assert r.valid and r.normalized == "27AAPFU0939F1ZV"
    assert r.details["pan"] == "AAPFU0939F"
    assert not validate_gstin("27AAPFU0939F1Z0").valid
    assert validate_gstin("27AAPFU0939F1Z0").reason == "BAD_CHECKSUM"
    assert validate_gstin("99AAAAA0000A1Z5").reason in ("UNKNOWN_STATE", "BAD_CHECKSUM")


def test_pan_ifsc():
    assert validate_pan("AAAPC1234F").valid
    assert validate_pan("AAAPC1234F").details["entity"] == "P"
    assert not validate_pan("ABC123").valid
    assert validate_ifsc("HDFC0001234").valid
    assert not validate_ifsc("HDFC001234").valid


def test_aba():
    assert aba_valid("011000015")
    assert validate_aba("011000015").valid
    assert validate_aba("011000014").reason == "BAD_CHECKSUM"
    assert validate_ein("84-1234567").valid
    assert validate_ein("00-1234567").reason == "UNKNOWN_PREFIX"


def test_iban_swift():
    assert validate_iban("DE89370400440532013000").valid
    assert validate_iban("GB29NWBK60161331926819").valid
    assert validate_iban("DE89370400440532013001").reason == "BAD_CHECKSUM"
    assert validate_swift("DEUTDEFF").valid
    assert validate_swift("DEUTDEFF500").valid
    assert not validate_swift("XX").valid


def test_vat():
    assert validate_gb_vat("GB999999973").valid
    assert not validate_gb_vat("GB980780858").valid
    assert validate_de_vat("DE812415868").valid
    assert not validate_de_vat("DE123").valid
    assert not validate_de_vat("DE012345678").valid


def test_phone_postal():
    assert validate_phone("+1 614 555 0142", "US").valid
    assert validate_postal("43215", "US").valid
    assert validate_postal("400001", "IN").valid
    assert not validate_postal("000000", "IN").valid
