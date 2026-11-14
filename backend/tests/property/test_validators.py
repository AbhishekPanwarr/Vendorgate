"""Property tests: own validators vs stdnum oracle + single-char mutation detection."""

import random

from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from stdnum import iban as std_iban
from stdnum.de import vat as std_de
from stdnum.gb import vat as std_gb

from backend.app.validators.ein import validate_aba
from backend.app.validators.gstin import gstin_check_char
from backend.app.validators.gstin import validate_gstin
from backend.app.validators.iban import validate_iban
from backend.app.validators.vat import validate_de_vat
from backend.app.validators.vat import validate_gb_vat


def _mutate(s: str, rng: random.Random) -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    i = rng.randrange(len(s))
    choices = [c for c in chars if c != s[i]]
    return s[:i] + rng.choice(choices) + s[i + 1 :]


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**63))
def test_iban_oracle_agreement(seed):
    rng = random.Random(seed)
    cc = rng.choice(["DE", "GB", "FR", "IT", "ES", "NL", "IE"])
    ln = {"DE": 22, "GB": 22, "FR": 27, "IT": 27, "ES": 24, "NL": 18, "IE": 22}[cc]
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    num = cc + "".join(rng.choice(alpha) for _ in range(ln - 2))
    assert validate_iban(num).valid == std_iban.is_valid(num)


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**63))
def test_vat_oracle_agreement(seed):
    rng = random.Random(seed)
    for mod, ora, pre in (
        (validate_gb_vat, std_gb.is_valid, "GB"),
        (validate_de_vat, std_de.is_valid, "DE"),
    ):
        d = "".join(str(rng.randint(0, 9)) for _ in range(9))
        assert mod(pre + d).valid == ora(pre + d)


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**63))
def test_single_char_mutation_detected(seed):
    rng = random.Random(seed)

    def _invalid_found(valid_id: str, check) -> bool:
        for _ in range(200):
            m = _mutate(valid_id, rng)
            if m != valid_id and not check(m).valid:
                return True
        return False

    base14 = "27AAPFU0939F1Z"[:14]
    valid_gstin = base14 + gstin_check_char(base14)
    assert validate_gstin(valid_gstin).valid
    assert _invalid_found(valid_gstin, validate_gstin)

    assert validate_aba("011000015").valid
    assert _invalid_found("011000015", validate_aba)

    valid_iban = "DE89370400440532013000"
    assert validate_iban(valid_iban).valid
    assert _invalid_found(valid_iban, validate_iban)
