from backend.app.adapters.base import Verifier
from backend.app.adapters.mocks.verifiers import BankMock
from backend.app.adapters.mocks.verifiers import GstMock
from backend.app.adapters.mocks.verifiers import IrsMock
from backend.app.adapters.mocks.verifiers import RegistryMock
from backend.app.adapters.mocks.verifiers import ViesMock


def test_protocol_conformance():
    for cls in (IrsMock, GstMock, ViesMock, RegistryMock, BankMock):
        assert isinstance(cls(), Verifier)


def test_irs_hit_and_miss():
    import anyio

    r = anyio.run(IrsMock().verify, {"tax_id": "841234567"})
    assert r.status.value == "OK" and r.fixture_id == "irs-hp1"
    assert r.data["code"] == 0
    r2 = anyio.run(IrsMock().verify, {"tax_id": "999999999"})
    assert r2.status.value == "NOT_FOUND"


def test_gst_vies_registry_bank():
    import anyio

    assert anyio.run(GstMock().verify, {"gstin": "29AAPCA1234F1ZR"}).status.value == "OK"
    assert anyio.run(ViesMock().verify, {"vat_id": "DE812415868"}).status.value == "OK"
    r = anyio.run(RegistryMock().verify, {"name_key": "meridian shipping services ltd"})
    assert r.data["status"] == "Active"
    r2 = anyio.run(BankMock().verify, {"acct_key": "US|011000015|000123456789"})
    assert r2.data["holder_name"] == "Brightline Office Supply LLC"
