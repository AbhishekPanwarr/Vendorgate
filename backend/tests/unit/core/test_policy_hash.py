from backend.app.core.policy import load_policy


def test_policy_hash_stable():
    p1 = load_policy("policy")
    p2 = load_policy("policy")
    assert p1.version == p2.version


def test_policy_hash_changes_on_edit(tmp_path):
    import shutil

    shutil.copytree("policy", tmp_path / "policy")
    p1_version = load_policy("policy").version
    with open(tmp_path / "policy" / "base.yaml", "a") as fh:
        fh.write("\nscoring_extra: 1\n")
    p2_version = load_policy(str(tmp_path / "policy")).version
    assert p1_version != p2_version


def test_hash_for_differs():
    p = load_policy("policy")
    assert p.hash_for("C-TAX-01") != p.hash_for("C-TAX-02")
