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
    assert all(o["carrier"] != "USPS" for o in q["options"])
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
