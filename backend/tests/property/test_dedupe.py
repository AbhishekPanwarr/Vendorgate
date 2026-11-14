from backend.app.core.hashing import fingerprint
from backend.app.network import graph as net


def test_fingerprint_changes_with_adapter_version():
    base = dict(
        check_id="C-VER-01",
        version=1,
        subject=None,
        policy_hash="p",
        reads={"tax.tax_id": "x"},
        adapters={"irs": "0.1.0"},
        lists={},
    )
    a = fingerprint(**base)
    b = fingerprint(**{**base, "adapters": {"irs": "0.2.0"}})
    assert a != b


def test_same_bank_key_always_dup():
    from backend.app.network.graph import seed_master

    seed_master()
    k = net.bank_key("IN", "HDFC0001234", "987654321098")
    hits = net.find_bank_reuse(k)
    assert hits and hits[0]["vendor_id"] == "V-000044"
    assert net.find_bank_reuse(net.bank_key("IN", "HDFC0001234", "000000000000")) == []
