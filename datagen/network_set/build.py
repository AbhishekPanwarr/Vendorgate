"""Network test set: 15 planted clusters of 2-4 vendors sharing 2+ attributes."""

import json
import random
from pathlib import Path

OUT = Path("datagen/network_set")


def build(seed=42):
    rng = random.Random(seed)
    with open("datagen/out/world.json") as fh:
        world = json.load(fh)
    vendors = [v for v in world["vendors"] if "-B" not in v["vendor_id"]]
    clusters = []
    used = set()
    for i in range(15):
        size = rng.choice([2, 3, 3, 4])
        pool = [v for v in vendors if v["vendor_id"] not in used]
        members = rng.sample(pool, size)
        for m in members:
            used.add(m["vendor_id"])
        anchor = members[0]
        # plant: share bank account + phone with anchor
        cluster = {"id": f"C-{i:02d}",
                   "members": [{"vendor_id": m["vendor_id"],
                                "legal_name": m["legal_name"],
                                "bank": anchor["bank"], "phone": anchor["phone"]}
                               for m in members]}
        clusters.append(cluster)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "clusters.json", "w") as fh:
        json.dump(clusters, fh, indent=1)
    print(f"network set: {len(clusters)} clusters")


if __name__ == "__main__":
    build()
