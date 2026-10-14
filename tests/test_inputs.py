"""Unknown filter values are errors that list the valid choices (not empty results), counts are true totals,
and long tool results are trimmed by whole rows with a note."""
import json

from conftest import headers

from app import assistant, db
from app.auth import load_employee


def test_unknown_warehouse_is_an_error_listing_the_codes(client, ids):
    r = client.get("/api/inventory", params={"warehouse": "Boston"}, headers=headers(ids["director"]))
    assert r.status_code == 400
    assert "Unknown warehouse 'Boston'" in r.json()["detail"] and "NWK (Newark, NJ)" in r.json()["detail"]


def test_warehouse_city_name_is_accepted(client, ids):
    r = client.get("/api/inventory", params={"warehouse": "Newark", "limit": 3}, headers=headers(ids["director"])).json()
    assert r["warehouse"] == "NWK" and r["count"] > 0


def test_unknown_order_status_is_an_error(client, ids):
    r = client.get("/api/orders", params={"status": "Pending"}, headers=headers(ids["cs"]))
    assert r.status_code == 400 and "Processing" in r.json()["detail"]


def test_category_matches_without_the_plural(client, ids):
    r = client.get("/api/inventory", params={"category": "brake pad", "limit": 3}, headers=headers(ids["cs"])).json()
    assert r["count"] > 0 and all(x["category"] == "Brake Pads" for x in r["results"])


def test_assistant_tool_gets_the_error_with_valid_choices(ids):
    text, is_err = assistant.run_tool(load_employee(ids["regional"]), "search_orders", {"warehouse": "Newerk"})
    assert is_err and "Unknown warehouse" in text and "NWK (Newark, NJ)" in text


def test_counts_are_true_totals_and_missing_sorts_by_missing(client, ids):
    expected = db.one("""SELECT COUNT(*) parts, SUM(m) units FROM (SELECT SUM(qty_missing) m FROM v_stock_position
                         WHERE warehouse_code = 'NWK' AND part_status = 'Active' GROUP BY part_id HAVING m > 0)""")
    r = client.get("/api/inventory", params={"warehouse": "NWK", "stock_filter": "missing", "limit": 10},
                   headers=headers(ids["director"])).json()
    assert r["count"] == 10 < r["total"] == expected["parts"]
    assert r["totals"]["qty_missing"] == expected["units"]
    missing = [x["qty_missing"] for x in r["results"]]
    assert missing == sorted(missing, reverse=True)


def test_order_and_transit_totals(client, ids):
    o = client.get("/api/orders", params={"limit": 5, "days": 365}, headers=headers(ids["director"])).json()
    assert o["count"] == 5 and o["total"] > 5
    t = assistant.run_tool(load_employee(ids["director"]), "find_in_transit", {"status": "customs hold"})
    d = json.loads(t[0])
    assert d["total"] == d["count"] > 0 and d["total_units"] == sum(s["units"] for s in d["shipments"])


def test_analytics_unknown_warehouse_is_an_error_and_out_of_scope_is_explained(client, ids):
    assert client.get("/api/analytics", params={"warehouse": "Boston"}, headers=headers(ids["director"])).status_code == 400
    d = client.get("/api/analytics", params={"warehouse": "Los Angeles"}, headers=headers(ids["wh_manager"])).json()
    assert d["scope_note"] and "LAX" in d["scope_note"]
    assert {r["label"] for r in d["inventory_by_warehouse"]} == {"ATL"}


def test_long_tool_results_are_trimmed_by_rows_with_a_note():
    out = {"total": 500, "results": [{"part_number": f"P{i:05d}", "note": "x" * 80} for i in range(500)]}
    txt = assistant._fit(out)
    assert len(txt) <= assistant.MAX_RESULT_CHARS
    d = json.loads(txt)                                       # still valid JSON, not cut mid-way
    assert d["total"] == 500 and 1 <= len(d["results"]) < 500
    assert f"shows {len(d['results'])} of 500 rows" in d["_shortened"]
    assert assistant._fit({"a": 1}) == '{"a": 1}'


def test_plural_search_words_find_singular_part_names(ids):
    from app import services
    emp = load_employee(ids["cs"])
    for plural, singular in [("spark plugs", "spark plug"), ("batteries", "battery"), ("rear rotors", "rear rotor")]:
        a = services.search_inventory(emp, q=plural)["total"]
        assert a > 0 and a == services.search_inventory(emp, q=singular)["total"], plural
    pn = db.scalar("SELECT part_number FROM parts WHERE status = 'Active' AND part_number LIKE '%S' LIMIT 1")
    assert any(r["part_number"] == pn for r in services.search_inventory(emp, q=pn)["results"])   # part numbers still match
