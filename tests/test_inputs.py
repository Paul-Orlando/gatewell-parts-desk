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


# --------------------------------------------------------------------------- analytics sections (live test fix F)
META = {"period", "warehouse", "category", "note", "scope", "scope_note", "as_of", "warehouses"}


def test_analytics_sections_list_matches_the_dashboard(ids):
    from app import analytics
    d = analytics.dashboard(load_employee(ids["director"]), "all")
    assert set(d) - META == set(analytics.SECTIONS)
    schema = assistant.TOOL_BY_NAME["analytics_summary"]["schema"]["properties"]["sections"]
    assert schema["items"]["enum"] == list(analytics.SECTIONS)
    desc = assistant.TOOL_BY_NAME["analytics_summary"]["description"]
    assert all(f"{k}: " in desc for k in analytics.SECTIONS)


def test_unknown_analytics_section_is_rejected(ids):
    text, is_err = assistant.run_tool(load_employee(ids["director"]), "analytics_summary", {"sections": ["missing_by_warehouse"]})
    assert is_err and "Unknown analytics section" in text and "inventory_by_warehouse" in text


def test_missing_value_per_warehouse_for_cost_roles_only(ids):
    expected = db.one("""SELECT SUM(qty_missing) units, ROUND(SUM(qty_missing * unit_cost_usd)) value
                         FROM inventory WHERE warehouse_code = 'NWK'""")
    d = json.loads(assistant.run_tool(load_employee(ids["director"]), "analytics_summary",
                                      {"period": "all", "sections": ["inventory_by_warehouse"]})[0])
    nwk = next(r for r in d["inventory_by_warehouse"] if r["label"] == "NWK")
    assert nwk["missing"] == expected["units"] == 140 and nwk["missing_value_usd"] == expected["value"]
    assert max(d["inventory_by_warehouse"], key=lambda r: r["missing"])["label"] == "NWK"
    sup = json.loads(assistant.run_tool(load_employee(ids["cs_sup"]), "analytics_summary",
                                        {"period": "all", "sections": ["inventory_by_warehouse"]})[0])
    assert all("missing_value_usd" not in r and "missing" in r for r in sup["inventory_by_warehouse"])


# --------------------------------------------------------------------------- analytics category filter
def _brakes_sql(warehouses=None):
    """Direct SQL for the Brakes group, optionally limited to some warehouses."""
    w = f" AND warehouse_code IN ({','.join('?' * len(warehouses))})" if warehouses else ""
    stock = db.one(f"""SELECT SUM(qty_on_hand) units, SUM(qty_missing) missing FROM v_stock_position
                       WHERE category_group = 'Brakes' {w}""", *(warehouses or []))
    ow = f" AND o.fulfillment_warehouse IN ({','.join('?' * len(warehouses))})" if warehouses else ""
    revenue = db.scalar(f"""SELECT ROUND(SUM(ol.line_total_usd)) FROM order_lines ol JOIN orders o USING (order_id)
                            JOIN parts p USING (part_id) WHERE p.category_group = 'Brakes' AND o.status <> 'Cancelled' {ow}""",
                        *(warehouses or []))
    return stock, revenue


def _group_of(part_number):
    return db.scalar("SELECT category_group FROM parts WHERE part_number = ?", part_number)


def test_category_narrows_every_section(client, ids):
    d = client.get("/api/analytics", params={"period": "all", "category": "Brakes"}, headers=headers(ids["director"])).json()
    stock, revenue = _brakes_sql()
    assert d["category"] == "Brakes" and d["note"]
    assert [r["label"] for r in d["inventory_by_group"]] == ["Brakes"] == [r["label"] for r in d["sales_by_group"]]
    assert [r["label"] for r in d["missing_by_group"]] in (["Brakes"], [])
    assert d["kpis"]["units_on_hand"] == stock["units"] and d["kpis"]["units_missing"] == stock["missing"]
    assert abs(d["kpis"]["revenue_usd"] - revenue) <= 1                # whole dollars, summed per order first
    assert sum(r["units"] for r in d["inventory_by_warehouse"]) == stock["units"]
    assert {_group_of(r["part_number"]) for r in d["low_stock"] + d["top_parts"]} == {"Brakes"}
    assert [r["label"] for r in d["price_by_group"]] == ["Brakes"]
    # shipping and FX are per order, so they're left out with a note
    assert d["shipping_by_carrier"] == [] and d["shipping_by_service"] == []
    assert d["kpis"]["carrier_cost_usd"] is None and d["kpis"]["fx_gain_loss_usd"] is None
    assert all(r["carrier_cost_usd"] is None for r in d["sales_by_month"])


def test_categories_add_up_to_the_whole(client, ids):
    from app import analytics, services
    od = load_employee(ids["director"])
    whole = analytics.dashboard(od, "all")
    parts = [analytics.dashboard(od, "all", category=g) for g in services.category_groups()]
    assert sum(p["kpis"]["units_on_hand"] for p in parts) == whole["kpis"]["units_on_hand"]
    assert abs(sum(p["kpis"]["revenue_usd"] for p in parts) - whole["kpis"]["revenue_usd"]) <= len(parts)   # rounding
    assert whole["note"] is None and whole["category"] == "All categories" and whole["shipping_by_carrier"]


def test_category_keeps_the_warehouse_scope(client, ids):
    wm = client.get("/api/analytics", params={"period": "all", "category": "Brakes"}, headers=headers(ids["wh_manager"])).json()
    stock, revenue = _brakes_sql(["ATL"])
    assert {r["label"] for r in wm["inventory_by_warehouse"]} == {"ATL"}
    assert wm["kpis"]["units_on_hand"] == stock["units"] and abs(wm["kpis"]["revenue_usd"] - revenue) <= 1
    assert {r["warehouse_code"] for r in wm["low_stock"]} <= {"ATL"}
    # asking for another warehouse with a category can't widen the view
    spoof = client.get("/api/analytics", params={"period": "all", "category": "Brakes", "warehouse": "LAX"},
                       headers=headers(ids["wh_manager"])).json()
    assert {r["label"] for r in spoof["inventory_by_warehouse"]} == {"ATL"} and spoof["scope_note"]
    assert spoof["kpis"]["units_on_hand"] == stock["units"]
    reg = client.get("/api/analytics", params={"period": "all", "category": "Sensors"}, headers=headers(ids["regional"])).json()
    assert {r["label"] for r in reg["inventory_by_warehouse"]} == {"NWK"}


def test_unknown_category_is_rejected(client, ids):
    r = client.get("/api/analytics", params={"category": "Tyres"}, headers=headers(ids["director"]))
    assert r.status_code == 400 and "Unknown category 'Tyres'" in r.json()["detail"] and "Brakes" in r.json()["detail"]


def test_assistant_analytics_tool_takes_a_category(ids):
    from app import services
    schema = assistant.TOOL_BY_NAME["analytics_summary"]["schema"]["properties"]["category"]
    assert schema["enum"] == services.category_groups()
    d = json.loads(assistant.run_tool(load_employee(ids["director"]), "analytics_summary",
                                      {"period": "all", "category": "Sensors", "sections": ["missing_by_group"]})[0])
    assert d["category"] == "Sensors" and [r["label"] for r in d["missing_by_group"]] == ["Sensors"]
    text, is_err = assistant.run_tool(load_employee(ids["director"]), "analytics_summary", {"category": "Tyres"})
    assert is_err and "Unknown category" in text


# --------------------------------------------------------------------------- part drawer: last 12 months of sales
def test_part_sales_cover_the_last_12_months_with_zeros(client, ids):
    from app import services
    r = client.get("/api/parts/KV8Z-9402-Y", headers=headers(ids["director"])).json()
    months = [m["order_month"] for m in r["monthly_sales"]]
    end = db.as_of()
    assert len(months) == 12 and months[-1] == f"{end.year:04d}-{end.month:02d}" and months == sorted(months)
    for m in r["monthly_sales"]:
        expected = db.scalar("SELECT COALESCE(SUM(quantity), 0) FROM v_sales WHERE part_number = ? AND order_month = ?",
                             "KV8Z-9402-Y", m["order_month"])
        assert m["units"] == expected
    assert services._last_12_months([])[0]["units"] == 0                       # months without sales are zero


def test_part_sales_follow_the_warehouse_scope(client, ids):
    wh = client.get("/api/parts/KV8Z-9402-Y", headers=headers(ids["warehouse"])).json()["monthly_sales"]
    for m in wh:
        expected = db.scalar("""SELECT COALESCE(SUM(quantity), 0) FROM v_sales WHERE part_number = ? AND order_month = ?
                                AND fulfillment_warehouse = 'ATL'""", "KV8Z-9402-Y", m["order_month"])
        assert m["units"] == expected and "revenue_usd" not in m
