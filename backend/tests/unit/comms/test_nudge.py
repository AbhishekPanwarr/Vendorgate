from backend.app.scheduler.jobs import _open_vendor_items
from backend.app.scheduler.jobs import render_nudge


def test_nudge_items_and_checker():
    from backend.app.comms.messages import check_message

    items = [{"fix_code": "PROVIDE_GSTIN", "title": "Provide GSTIN"}]
    body = render_nudge("c1", items)
    assert "[[PROVIDE_GSTIN]]" in body and "/resubmit" in body
    assert check_message("Reminder", body, items, status="PENDING") == []
    assert _open_vendor_items("no-such-case") == []
