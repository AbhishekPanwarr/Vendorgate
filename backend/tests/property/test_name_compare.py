from hypothesis import given
from hypothesis import strategies as st

from backend.app.core.policy import load_policy
from backend.app.matching.name_compare import compare_names
from backend.app.matching.name_compare import parse_name

CFG = load_policy("policy").raw["base"]["matching"]["name"]
WORDS = st.sampled_from(
    ["acme", "trading", "global", "services", "holdings", "beta", "north", "labs"]
)


@given(
    st.lists(WORDS, min_size=1, max_size=4, unique=True),
    st.lists(WORDS, min_size=1, max_size=4, unique=True),
)
def test_symmetric_relation(a, b):
    na, nb = " ".join(a), " ".join(b)
    r1 = compare_names(parse_name(na), parse_name(nb), CFG).relation
    r2 = compare_names(parse_name(nb), parse_name(na), CFG).relation
    assert r1 == r2 or {r1, r2} <= {"EXACT", "EQUIVALENT"}


@given(st.lists(WORDS, min_size=2, max_size=4, unique=True))
def test_strict_subset_never_exact(words):
    full = " ".join(words)
    sub = " ".join(words[:-1])
    r = compare_names(parse_name(sub), parse_name(full), CFG).relation
    assert r not in ("EXACT", "EQUIVALENT")
