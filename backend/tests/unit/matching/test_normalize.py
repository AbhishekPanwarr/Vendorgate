from backend.app.matching.normalize import canon_address
from backend.app.matching.normalize import canon_domain
from backend.app.matching.normalize import canon_id
from backend.app.matching.normalize import canon_money
from backend.app.matching.normalize import canon_phone
from backend.app.matching.normalize import canon_text


def test_canon_text_idempotent():
    for s in ["  Acme  Trading\tCo ", "Café — Münchén", "ACME"]:
        a, _ = canon_text(s)
        b, _ = canon_text(a)
        assert a == b


def test_mixed_script_before_unidecode():
    _, m = canon_text("Acme Trading Co")
    assert m is False
    _, m = canon_text("Acmе Trading Co")  # Cyrillic е
    assert m is True
    # Roman-numeral lookalike is Latin-adjacent, not Cyrillic/Greek: out of scope
    _, m = canon_text("Ⅽompany Services")
    assert m is False


def test_canon_id_phone_domain():
    assert canon_id("84-123 4567") == "841234567"
    assert canon_phone("+1 614 555 0142", "US") == "+16145550142"
    assert canon_phone("not a phone", "US") is None
    assert canon_domain("https://www.Acme.com/path") == "acme.com"
    assert canon_domain("user@gmail.com") == "gmail.com"
    assert canon_money(100, "INR") == 1.2


def test_canon_address():
    a = canon_address(
        {
            "line1": "410 Market St",
            "city": "Columbus",
            "region": "OH",
            "postal_code": "43215",
            "country": "US",
        }
    )
    assert "street" in a and "410" in a
