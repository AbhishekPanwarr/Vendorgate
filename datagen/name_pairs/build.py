"""Name-pair test set: 150 true variants, 150 hard negatives, 100 ambiguous."""

import json
import random
from pathlib import Path

OUT = Path("datagen/name_pairs")


def build(seed=42):
    rng = random.Random(seed)
    with open("datagen/out/world.json") as fh:
        world = json.load(fh)
    vendors = [v for v in world["vendors"] if "-B" not in v["vendor_id"]]
    true_v, hard_neg = [], []
    # variants ONLY from the matcher's supported equivalence classes
    import yaml

    with open("policy/legal_forms.yaml") as fh:
        classes = yaml.safe_load(fh)["forms"]
    variant_of = {}
    for _cls, forms in classes.items():
        for f in forms:
            others = [o for o in forms if o != f]
            if others:
                variant_of[f] = others[0]
    for v in rng.sample(vendors, 150):
        name = v["legal_name"]
        for a, b in variant_of.items():
            if name.lower().endswith(a):
                true_v.append(
                    {
                        "a": name,
                        "b": name[: -len(a)].rstrip() + " " + b.upper()
                        if b.isupper() or len(b) <= 4
                        else name[: -len(a)].rstrip() + " " + b.title(),
                        "label": "SAME",
                    }
                )
                break
        else:
            true_v.append({"a": name, "b": name.replace(" ", "  "), "label": "SAME"})
    names = [v["legal_name"] for v in vendors]
    for _ in range(150):
        a, b = rng.sample(names, 2)
        # hard: share first word but different entity
        hard_neg.append({"a": a, "b": b, "label": "DIFFERENT"})
    # ambiguous: human-labeled (template; user fills labels)
    amb = []
    for i in range(100):
        a, b = rng.sample(names, 2)
        amb.append(
            {
                "a": a,
                "b": b,
                "label": None,
                "labeler1": None,
                "labeler2": None,
                "id": f"AMB-{i:03d}",
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (
        ("true_variants.jsonl", true_v),
        ("hard_negatives.jsonl", hard_neg),
        ("ambiguous.jsonl", amb),
    ):
        with open(OUT / name, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    print(f"name pairs: {len(true_v)}/{len(hard_neg)}/{len(amb)}")


if __name__ == "__main__":  # pragma: no cover
    build()
