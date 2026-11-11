"""World generator smoke: per-country vendors validate (no pipeline)."""

import random


def test_golden_vendors_validate():
    from backend.app.validators.ein import validate_aba, validate_ein
    from backend.app.validators.gstin import validate_gstin, validate_pan
    from backend.app.validators.iban import validate_iban
    from datagen.world import golden_vendor
    from stdnum.de import vat as dev
    from stdnum.gb import vat as gbv

    rng = random.Random(3)
    for country in ("US", "IN", "GB", "DE"):
        v = golden_vendor(rng, country, 0)
        assert v["country"] == country
        if country == "IN":
            assert validate_gstin(v["tax"]["tax_id"]).valid
            assert validate_pan(v["tax"]["pan"]).valid
        elif country == "US":
            assert validate_ein(v["tax"]["tax_id"]).valid
            assert validate_aba(v["bank"]["routing_number"]).valid
        elif country == "GB":
            assert gbv.is_valid(v["tax"]["tax_id"])
            assert validate_iban(v["bank"]["iban"]).valid
        else:
            assert dev.is_valid(v["tax"]["tax_id"])
            assert validate_iban(v["bank"]["iban"]).valid


def test_world_determinism():
    from datagen.world import build_world

    w1 = build_world(42)
    w2 = build_world(42)
    assert [v["vendor_id"] for v in w1["vendors"]] == [v["vendor_id"] for v in w2["vendors"]]
    assert len(w1["sanctions"]) == 120 and len(w1["decoys"]) == 12
