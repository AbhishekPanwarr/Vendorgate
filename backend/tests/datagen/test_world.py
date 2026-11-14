import json


def _world():
    with open("datagen/out/world.json") as fh:
        return json.load(fh)


def _manifest():
    with open("datagen/out/world_manifest.json") as fh:
        return json.load(fh)


def test_counts():
    w = _world()
    assert len(w["vendors"]) == 160
    assert len(w["sanctions"]) == 120
    assert len(w["decoys"]) == 12 and len(w["variants"]) == 12
    assert len(w["pep"]) == 30 and len(w["adverse"]) == 40
    assert len(w["virtual_offices"]) == 20


def test_ids_validate():
    from backend.app.validators.ein import validate_aba
    from backend.app.validators.ein import validate_ein
    from backend.app.validators.gstin import validate_gstin
    from backend.app.validators.gstin import validate_pan
    from backend.app.validators.iban import validate_iban
    from stdnum.de import vat as dev
    from stdnum.gb import vat as gbv

    for v in _world()["vendors"]:
        c = v["country"]
        if c == "IN":
            assert validate_gstin(v["tax"]["tax_id"]).valid, v["vendor_id"]
            assert validate_pan(v["tax"]["pan"]).valid, v["vendor_id"]
        elif c == "US":
            assert validate_ein(v["tax"]["tax_id"]).valid, v["vendor_id"]
            assert validate_aba(v["bank"]["routing_number"]).valid, v["vendor_id"]
        elif c == "GB":
            assert gbv.is_valid(v["tax"]["tax_id"]), v["vendor_id"]
            assert validate_iban(v["bank"]["iban"]).valid, v["vendor_id"]
        else:
            assert dev.is_valid(v["tax"]["tax_id"]), v["vendor_id"]
            assert validate_iban(v["bank"]["iban"]).valid, v["vendor_id"]


def test_decoys_contradict():
    for d in _world()["decoys"]:
        assert d["country"] == "XX" and d["incorporation_year"] == 1990


def test_determinism():
    import hashlib

    with open("datagen/out/world.json", "rb") as fh:
        blob = fh.read()
    assert _manifest()["sha256"] == hashlib.sha256(blob).hexdigest()
