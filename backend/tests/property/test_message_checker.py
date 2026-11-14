from backend.app.comms.messages import check_message


def _items(*codes):
    return [{"fix_code": c, "title": c, "what": "fix it", "field_paths": []} for c in codes]


def _body(codes):
    lines = [
        "Hi, fix these:",
        *[f"{i}. [[{c}]] title: what" for i, c in enumerate(codes, 1)],
        "resubmit by Friday. [Resubmit → /resubmit]",
    ]
    return "\n".join(lines)


def test_exact_once():
    items = _items("A", "B")
    assert check_message("s", _body(["A", "B"]), items) == []
    assert any("A" in e for e in check_message("s", _body(["B"]), items))
    errs = check_message("s", _body(["A", "B", "C"]), items)
    assert any("extra" in e and "C" in e for e in errs)


def test_forbidden_deadline_length():
    items = _items("A")
    bad = _body(["A"]).replace("/resubmit", "") + " sanction review needed"
    errs = check_message("s", bad, items)
    assert any("forbidden" in e for e in errs)
    no_link = _body(["A"]).replace("[Resubmit → /resubmit]", "")
    assert any("resubmit" in e for e in check_message("s", no_link, items))
    long_body = _body(["A"]) + " word " * 400
    assert any("350" in e for e in check_message("s", long_body, items))
