"""Synthetic world: golden vendors, registries, sanctions/PEP/adverse lists.

Deterministic on SEED. Labels NEVER come from the pipeline (see
test_label_independence.py).
"""

import hashlib
import json
import random
from pathlib import Path

from backend.app.validators.gstin import gstin_check_char

OUT = Path("datagen/out")
SEED_DEFAULT = 42

FIRST = [
    "Acme",
    "Brightline",
    "Nimbus",
    "Helios",
    "Meridian",
    "Northwind",
    "Beacon",
    "Hafen",
    "Rhein",
    "Summit",
    "Kappa",
    "Omnitech",
    "Pinnacle",
    "Redwood",
    "Bluefin",
    "Harbor",
    "Zenith",
    "Apex",
    "Delta",
    "Cobalt",
]
SECOND = [
    "Trading",
    "Logistics",
    "Technologies",
    "Freight",
    "Shipping",
    "Retail",
    "Office",
    "Container",
    "Systems",
    "Labs",
    "Foods",
    "Medical",
    "Ventures",
    "Holdings",
    "Supply",
]
FORMS = {
    "US": ["LLC", "Inc", "Corp"],
    "IN": ["Pvt Ltd", "Limited", "LLP"],
    "GB": ["Ltd", "PLC"],
    "DE": ["GmbH", "AG", "UG"],
}
PHONES = {"US": "+1555013", "IN": "+9198100", "GB": "+44207123", "DE": "+493012"}


def _gstin(rng, state="29"):
    pan_letters = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(3))
    pan_letters += "C" + rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    pan = f"{pan_letters}{rng.randint(1000, 9999):04d}{rng.choice('CFAT')}"
    base = (state + pan + rng.choice("123456789ABCDEF") + "Z")[:14]
    return base + gstin_check_char(base), pan


def _ein(rng):
    prefix = rng.choice(["84", "52", "12", "36", "61", "77"])
    return f"{prefix}-{rng.randint(1000000, 9999999):07d}"


def _aba(rng):
    from backend.app.validators.ein import aba_valid

    while True:
        r = "".join(str(rng.randint(0, 9)) for _ in range(9))
        if aba_valid(r):
            return r


def _iban(rng, country):
    from stdnum import iban as _iban_mod

    if country == "DE":
        bban = "".join(str(rng.randint(0, 9)) for _ in range(18))
    else:
        bank = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(4))
        bban = bank + "".join(str(rng.randint(0, 9)) for _ in range(14))
    num = "".join(str(int(c, 36)) for c in (bban + country + "00"))
    check = 98 - int(num) % 97
    cand = f"{country}{check:02d}{bban}"
    assert _iban_mod.is_valid(cand), cand
    return cand


def _de_vat(rng):
    from stdnum.de import vat as _dev

    while True:
        d = "".join(str(rng.randint(0, 9)) for _ in range(9))
        if d[0] != "0" and _dev.is_valid("DE" + d):
            return "DE" + d


def _gb_vat(rng):
    from stdnum.gb import vat as _gbv

    while True:
        d = "".join(str(rng.randint(0, 9)) for _ in range(9))
        if _gbv.is_valid("GB" + d):
            return "GB" + d


def golden_vendor(rng, country, idx):
    name = f"{rng.choice(FIRST)} {rng.choice(SECOND)} {rng.choice(FORMS[country])}"
    tax = {}
    bank = {"country": country}
    if country == "US":
        tax = {"tax_id": _ein(rng), "form": "W9"}
        bank.update(
            {
                "routing_number": _aba(rng),
                "account_number": "".join(str(rng.randint(0, 9)) for _ in range(12)),
                "currency": "USD",
            }
        )
    elif country == "IN":
        gstin, pan = _gstin(rng)
        tax = {"tax_id": gstin, "pan": pan, "form": "GST_CERT"}
        bank.update(
            {
                "ifsc": f"HDFC0{rng.randint(0, 999999):06d}",
                "account_number": "".join(str(rng.randint(0, 9)) for _ in range(12)),
                "currency": "INR",
            }
        )
    elif country == "GB":
        iban = _iban(rng, "GB")
        tax = {"tax_id": _gb_vat(rng), "form": "VAT_CERT"}
        bank.update(
            {
                "iban": iban,
                "account_number": "".join(ch for ch in iban[4:] if ch.isdigit())[-10:],
                "currency": "GBP",
            }
        )
    else:
        iban = _iban(rng, "DE")
        tax = {"tax_id": _de_vat(rng), "form": "VAT_CERT"}
        bank.update(
            {
                "iban": iban,
                "account_number": "".join(ch for ch in iban[4:] if ch.isdigit())[-10:],
                "currency": "EUR",
            }
        )
    domain = "".join(name.lower().split())[:24].replace(".", "") + ".example"
    return {
        "vendor_id": f"G-{country}-{idx:03d}",
        "legal_name": name,
        "country": country,
        "tax": tax,
        "bank": bank,
        "email": f"ap@{domain}",
        "phone": f"{PHONES[country]}{rng.randint(1000, 9999):04d}",
        "category": rng.choice(["OFFICE_SUPPLIES", "IT_SERVICES", "LOGISTICS", "CONSULTING"]),
        "spend": rng.choice([2000, 18000, 60000, 120000]),
        "truth": {"registry_status": "Active", "incorporation_year": rng.randint(2008, 2023)},
    }


def build_world(seed=SEED_DEFAULT):
    rng = random.Random(seed)
    vendors = []
    counts = {"US": 40, "IN": 40, "GB": 35, "DE": 35}
    for country, n in counts.items():
        for i in range(n):
            vendors.append(golden_vendor(rng, country, i))
    # 10 near-similar pairs: clone with legal-form variant name
    for i in range(10):
        v = dict(rng.choice(vendors))
        v = json.loads(json.dumps(v))
        v["vendor_id"] += "-B"
        v["legal_name"] = v["legal_name"].replace("Ltd", "Limited").replace("LLC", "L.L.C.")
        vendors.append(v)
    sanctions = [
        {
            "id": f"S-{i:03d}",
            "type": "entity",
            "names": [f"Blocked Entity {i}"],
            "aliases": [],
            "country": rng.choice(["PA", "KP", "IR"]),
            "reg_no": f"X-{i}",
            "incorporation_year": rng.randint(1995, 2020),
            "addresses": [],
            "program": "MOCK-SDN",
        }
        for i in range(120)
    ]
    decoys, variants = [], []
    for i in range(12):
        v = rng.choice(vendors)
        decoys.append(
            {
                "id": f"D-{i:03d}",
                "near": v["legal_name"],
                "country": "XX",
                "incorporation_year": 1990,
            }
        )
        variants.append(
            {
                "id": f"V-{i:03d}",
                "near": v["legal_name"],
                "country": v["country"],
                "incorporation_year": v["truth"]["incorporation_year"],
            }
        )
    return {
        "seed": seed,
        "vendors": vendors,
        "sanctions": sanctions,
        "decoys": decoys,
        "variants": variants,
        "pep": [{"id": f"P-{i:03d}", "names": [f"Official Person {i}"]} for i in range(30)],
        "adverse": [
            {
                "id": f"A-{i:03d}",
                "subject": f"subject {i}",
                "category": rng.choice(["FRAUD", "CORRUPTION", "ENFORCEMENT", "LITIGATION"]),
                "severity": rng.choice(["HIGH", "LOW"]),
                "date": "2025-01-01",
            }
            for i in range(40)
        ],
        "virtual_offices": [f"{i} Virtual Plaza, Suite {i}" for i in range(1, 21)],
    }


def main(seed=SEED_DEFAULT) -> dict:
    world = build_world(seed)
    OUT.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(world, sort_keys=True)
    (OUT / "world.json").write_text(blob)
    manifest = {
        "seed": seed,
        "vendors": len(world["vendors"]),
        "sha256": hashlib.sha256(blob.encode()).hexdigest(),
    }
    (OUT / "world_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"world: {len(world['vendors'])} vendors, sha {manifest['sha256'][:12]}")
    return world


if __name__ == "__main__":  # pragma: no cover
    import sys

    seed = int(sys.argv[sys.argv.index("SEED") + 1]) if "SEED" in sys.argv else SEED_DEFAULT
    main(seed)
