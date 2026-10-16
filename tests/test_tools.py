"""Business rules in the tools: shipping restrictions, quotes, FAQ, live-person handoff, support cases."""
from app import agent_tools as AT
from app import db


def _part(category, extra=""):
    return db.scalar(f"""SELECT p.part_number FROM v_stock_position s JOIN parts p USING (part_id)
                         WHERE p.category = ? AND s.qty_available > 2 {extra} LIMIT 1""", category)


def test_battery_not_shipped_overseas():
    q = AT.quote_shipping([{"part_number": _part("12V Battery")}], "AE")
    assert not q["ok"] and "overseas" in q["message"]


def test_battery_ground_only_domestic():
    q = AT.quote_shipping([{"part_number": _part("12V Battery")}], "US", "IL")
    assert q["ok"] and {o["speed"] for o in q["options"]} == {"Ground"}
    assert any("ground" in u["reason"] for u in q["unavailable"])


def test_usps_refuses_bumper_and_no_free_oversize():
    q = AT.quote_shipping([{"part_number": _part("Front Bumper Cover")}], "US", "TX")
    assert q["ok"]
    assert all(o["carrier"] != "Postara" for o in q["options"])
    assert all(o["customer_pays_usd"] > 0 for o in q["options"])


def test_quotes_sorted_and_dated():
    q = AT.quote_shipping([{"part_number": _part("Oil Filter")}], "US", "GA")
    costs = [o["cost_usd"] for o in q["options"]]
    assert costs == sorted(costs) and len({o["carrier"] for o in q["options"]}) >= 3
    assert all(o["estimated_delivery_by"] >= o["ships_on"] for o in q["options"])


def test_full_quote_in_local_currency_with_tax():
    cust = db.scalar("SELECT customer_id FROM customers WHERE city = 'Toronto' AND customer_type = 'Individual' LIMIT 1")
    fq = AT.full_quote([{"part_number": _part("Oil Filter"), "quantity": 2}], customer_id=cust)
    assert fq["ok"] and fq["currency"] == "CAD"
    o = fq["options"][0]
    assert o["import_tax"] > 0 and abs(o["total"] - (o["parts"] + o["core_charges"] + o["shipping"] + o["import_tax"])) < 0.02


def test_faq_finds_policy():
    m = AT.search_faq("what is a core charge")["matches"]
    assert m and m[0]["question"] == "What is a core charge?" and m[0]["url"].startswith("https://")


def test_handoff_rules():
    assert AT.handoff_decision("Can I talk to a real person?")["handoff"]
    assert AT.handoff_decision("refund please", refund_amount_usd=480)["handoff"]
    assert AT.handoff_decision("question", failed_attempts=2)["handoff"]
    plain = AT.handoff_decision("What does a core charge mean?")
    assert not plain["handoff"] and plain["faq_suggestions"]


def test_after_hours_shows_next_opening_in_customer_time():
    c = AT.support_contact("EXP", customer_timezone="Asia/Riyadh")      # dataset time is Sunday afternoon in St. Louis
    assert not c["open_now"] and "Asia/Riyadh" in c["next_open"]


def test_create_support_case_writes_to_copy():
    cust = db.scalar("SELECT customer_id FROM customers LIMIT 1")
    before = db.scalar("SELECT COUNT(*) FROM support_cases")
    r = AT.create_support_case(cust, "CS", "Test case", db=db.DB_PATH)
    assert r["case_id"].startswith("CS-") and db.scalar("SELECT COUNT(*) FROM support_cases") == before + 1


def test_database_is_read_only_for_queries():
    import sqlite3
    import pytest
    con = db.read_conn()
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM inventory")


def test_handoff_never_claims_it_was_sent_or_queued():
    """A handoff saves nothing: it names the team and says nothing has been sent, open or closed."""
    from datetime import datetime, timezone
    for now in (datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc),       # Tuesday 10 AM Central: open
                datetime(2026, 10, 11, 21, 0, tzinfo=timezone.utc)):      # Sunday: closed
        h = AT.handoff_decision("customer wants a $400 refund", refund_amount_usd=400, now=now)
        text = h["message_to_customer"]
        assert h["handoff"] and text.startswith("This needs the Returns & Cores team.") and "Not yet sent" in text
        for claim in ("passed your question", "I'll connect you", "escalated", "Queued", "follow up"):
            assert claim not in text, claim
        assert h["case_status"] == "Not yet sent. Offer to open a support case."
    assert AT.handoff_decision("What does a core charge mean?")["case_status"] is None


def test_quote_with_no_stock_anywhere_says_after_stock_arrives():
    """IH-100009: 0 available anywhere, 120 inbound to ATL on Oct 14. Rates stay, the date doesn't."""
    q = AT.quote_shipping([{"part_number": "IH-100009"}], "US", "TX")
    assert q["ok"] and q["warehouse_code"] == "ATL" and q["all_in_stock"] is False
    line = q["lines"][0]
    assert line["stock_status"] == "Not in stock" and line["available_at_ship_from"] == 0
    assert line["next_inbound"]["warehouse"] == "ATL" and line["next_inbound"]["quantity"] == 120
    assert line["next_inbound"]["eta_local"].startswith("2026-10-14")
    assert q["options"] and all(o["cost_usd"] > 0 for o in q["options"])                 # rates are kept
    for o in q["options"]:
        assert o["estimated_delivery_by"] is None and o["ships_on"] is None
        assert o["delivery"].startswith("After stock arrives") and "Wed, Oct 14" in o["delivery"]
    assert any("isn't available at any warehouse" in n for n in q["notes"])
    f = AT.full_quote([{"part_number": "IH-100009"}], ship_to_state="TX")
    assert f["all_in_stock"] is False and f["lines"][0]["stock_status"] == "Not in stock"
    assert all(o["delivery_by"] is None and o["delivery"].startswith("After stock arrives") for o in f["options"])


def test_quote_in_stock_keeps_dates():
    q = AT.quote_shipping([{"part_number": "HL-100214"}], "US", "TX")
    assert q["all_in_stock"] and all(ln["stock_status"] == "In stock" for ln in q["lines"])
    assert all(o["estimated_delivery_by"] and "delivery" not in o for o in q["options"])


def test_quote_ships_from_the_warehouse_that_has_the_item():
    serving = db.scalar("SELECT serving_warehouse FROM states WHERE state_code = 'TX'")
    pn, wh = db.one("""SELECT p.part_number, MIN(s.warehouse_code) wh FROM v_stock_position s JOIN parts p USING (part_id)
                       WHERE s.qty_available > 0 AND p.hazmat = 0 AND p.status = 'Active'
                       GROUP BY p.part_id HAVING COUNT(*) = 1 AND MIN(s.warehouse_code) <> ? LIMIT 1""", serving).values()
    q = AT.quote_shipping([{"part_number": pn}], "US", "TX")
    assert q["warehouse_code"] == wh and q["all_in_stock"] and q["options"][0]["estimated_delivery_by"]


def test_support_teams_open_and_closed_in_central_time():
    from datetime import datetime, timezone
    from app import services
    snap = {t["department_id"]: t for t in services.support_teams(None)["teams"]}      # Sun, Oct 11, 4:00 PM Central
    assert not any(t["open_now"] for t in snap.values())
    assert snap["RET"]["department_name"] == "Returns & Cores" and snap["RET"]["phone"] == "(800) 555-0145"
    assert snap["RET"]["status"] == "Closed, opens Mon, Oct 12, 8:00 AM Central"
    tue = {t["department_id"]: t for t in services.support_teams(None, now=datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc))["teams"]}
    assert tue["RET"]["open_now"] and tue["RET"]["status"] == "Open now, until Tue, Oct 13, 5:00 PM Central"
    sat = {t["department_id"]: t["open_now"] for t in services.support_teams(None, now=datetime(2026, 10, 10, 15, 0, tzinfo=timezone.utc))["teams"]}
    assert sat == {"CS": True, "RET": True, "BIL": False, "DLR": False, "EXP": False}          # Sat 10 AM Central



def test_chargebacks_and_payment_disputes_go_to_billing():
    for msg in ("The customer is furious and says they'll file a chargeback.",
                "They want a refund or they'll file a chargeback.", "The customer disputed the charge on their card."):
        assert AT.handoff_decision(msg)["department_id"] == "BIL", msg
    assert AT.handoff_decision("customer wants a $400 refund", refund_amount_usd=400)["department_id"] == "RET"
