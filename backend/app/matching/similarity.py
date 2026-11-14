"""Name similarity: blended token_sort + Jaro-Winkler + trigram jaccard."""

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler


def ngram_jaccard(a: str, b: str, n: int = 3) -> float:
    ga = {a[i : i + n] for i in range(max(len(a) - n + 1, 1))}
    gb = {b[i : i + n] for i in range(max(len(b) - n + 1, 1))}
    if not ga and not gb:
        return 1.0
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def core_similarity(x: str, y: str, subset_cap: float = 0.88) -> float:
    ts, to = x.split(), y.split()
    sim = (
        0.5 * fuzz.token_sort_ratio(x, y)
        + 0.3 * JaroWinkler.similarity(x, y) * 100
        + 0.2 * ngram_jaccard(x, y) * 100
    ) / 100
    if set(ts) != set(to) and (set(ts) < set(to) or set(to) < set(ts)):
        sim = min(sim, subset_cap)
    return round(sim, 4)


def is_initialism(a: str, b: str) -> bool:
    aw, bw = a.split(), b.split()
    for short, words in ((aw, bw), (bw, aw)):
        if len(short) == 1 and len(short[0]) == len(words) and len(words) > 1:
            if all(w and w[0] == c for w, c in zip(words, short[0], strict=True)):
                return True
    return False
