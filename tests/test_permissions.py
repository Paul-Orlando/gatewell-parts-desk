"""Each role sees only what it should, and data scope limits warehouses - enforced by the server."""
import json
from conftest import headers

COST = {"unit_cost_usd", "stock_value_usd", "carrier_cost_usd", "shipping_margin_usd"}
MONEY = {"order_total_usd", "total_due_local", "payment_status", "line_total_usd"}


def _keys(obj):
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k); out |= _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _keys(v)
    return out


def test_sign_in_required(client):
    assert client.get("/api/inventory").status_code == 401
    assert client.get("/api/inventory", headers=headers("EMP-9999")).status_code == 401


def test_tabs_by_role(client, ids):
    tabs = {k: client.get("/api/me", headers=headers(v)).json()["employee"]["tabs"] for k, v in ids.items()}
    assert "analytics" not in tabs["warehouse"] and "cases" not in tabs["warehouse"]
    assert "cases" in tabs["cs"] and "analytics" not in tabs["cs"]
    assert "analytics" in tabs["cs_sup"] and "analytics" in tabs["director"]


def test_warehouse_staff_cannot_see_money_cost_or_customer_names(client, ids):
    h = headers(ids["warehouse"])
    inv = client.get("/api/inventory", params={"limit": 5}, headers=h).json()
    orders = client.get("/api/orders", params={"limit": 5}, headers=h).json()
    detail = client.get(f"/api/orders/{orders['results'][0]['order_id']}", headers=h).json()
    seen = _keys(inv) | _keys(orders) | _keys(detail)
    assert not seen & COST
    assert not seen & MONEY
    assert "customer_name" not in seen
    assert "list_price_usd" in seen                       # public list price stays visible


def test_warehouse_staff_only_see_their_warehouse_orders(client, ids):
    r = client.get("/api/orders", params={"limit": 200, "days": 365}, headers=headers(ids["warehouse"])).json()
    assert r["count"] > 0
    assert {o["fulfillment_warehouse"] for o in r["results"]} == {"ATL"}
    other = client.get("/api/orders", params={"warehouse": "LAX", "limit": 5}, headers=headers(ids["warehouse"])).json()
    assert all(o["fulfillment_warehouse"] == "ATL" for o in other["results"])


def test_customer_service_sees_prices_not_costs(client, ids):
    h = headers(ids["cs"])
    orders = client.get("/api/orders", params={"limit": 3}, headers=h).json()
    detail = client.get(f"/api/orders/{orders['results'][0]['order_id']}", headers=h).json()
    seen = _keys(orders) | _keys(detail)
    assert seen & MONEY and "customer_name" in seen
    assert not seen & COST


def test_analytics_and_cases_blocked_for_roles_without_access(client, ids):
    assert client.get("/api/analytics", headers=headers(ids["warehouse"])).status_code == 403
    assert client.get("/api/analytics", headers=headers(ids["cs"])).status_code == 403
    assert client.get("/api/cases", headers=headers(ids["warehouse"])).status_code == 403


def test_analytics_scope(client, ids):
    wh = client.get("/api/analytics", headers=headers(ids["wh_manager"])).json()
    reg = client.get("/api/analytics", headers=headers(ids["regional"])).json()
    co = client.get("/api/analytics", headers=headers(ids["director"])).json()
    assert {r["label"] for r in wh["inventory_by_warehouse"]} == {"ATL"}
    assert {r["label"] for r in reg["inventory_by_warehouse"]} == {"NWK"}       # the Northeast's warehouse
    assert len(co["inventory_by_warehouse"]) == 11
    assert co["kpis"]["units_on_hand"] > reg["kpis"]["units_on_hand"] > 0
    # a warehouse manager can't widen their view by asking for another warehouse
    spoof = client.get("/api/analytics", params={"warehouse": "LAX"}, headers=headers(ids["wh_manager"])).json()
    assert {r["label"] for r in spoof["inventory_by_warehouse"]} == {"ATL"}


def test_supervisor_analytics_hide_costs(client, ids):
    d = client.get("/api/analytics", headers=headers(ids["cs_sup"])).json()
    assert not _keys(d) & COST
    assert "revenue_usd" in d["kpis"]


# Customer-specific prices and shipping charges, and figures worked out from our costs
CUSTOMER_PRICE = {"subtotal_usd", "subtotal_local", "core_charge_local", "unit_price_usd", "unit_price_local"}
SHIPPING_CHARGES = {"cost_usd", "cost_local", "customer_pays_usd", "transportation_usd", "fuel_surcharge_usd",
                    "package_total_usd", "surcharges"}
DERIVED_COST = {"avg_cost_pct_of_list", "avg_carrier_cost_usd", "cost_pct_of_revenue", "shipping_cost_pct_of_revenue"}


def _dealer_with_discount():
    from app import db
    return db.one("SELECT customer_id, discount_pct FROM customers WHERE customer_type = 'Dealership' AND discount_pct > 0 "
                  "AND billing_currency = 'USD' ORDER BY customer_id LIMIT 1")


def test_warehouse_staff_cannot_get_a_customer_price_from_the_assistant(ids):
    from app import assistant, db
    from app.auth import load_employee
    pn = db.scalar("SELECT part_number FROM parts WHERE status = 'Active' AND list_price_usd > 50 ORDER BY part_number LIMIT 1")
    dealer = _dealer_with_discount()
    txt, err = assistant.run_tool(load_employee(ids["warehouse"]), "get_part_price",
                                  {"part_number": pn, "customer_id": dealer["customer_id"]})
    assert not err
    import json
    out = json.loads(txt)
    assert not _keys(out) & (CUSTOMER_PRICE | MONEY)
    list_price = db.scalar("SELECT list_price_usd FROM parts WHERE part_number = ?", pn)
    dealer_price = round(list_price * (1 - dealer["discount_pct"]), 2)
    assert f"{dealer_price}" not in txt and f"{dealer_price:.2f}" not in txt
    # customer service still gets the dealer price
    cs, _ = assistant.run_tool(load_employee(ids["cs"]), "get_part_price", {"part_number": pn, "customer_id": dealer["customer_id"]})
    assert json.loads(cs)["subtotal_usd"] == dealer_price


def test_warehouse_shipping_quote_hides_charges_but_keeps_options(client, ids):
    from app import db
    pn = db.scalar("""SELECT p.part_number FROM parts p JOIN v_stock_position s ON s.part_id = p.part_id
                      WHERE p.status = 'Active' AND p.hazmat = 0 AND s.warehouse_code = 'ATL' AND s.qty_available > 0
                      ORDER BY p.part_number LIMIT 1""")
    body = {"items": [{"part_number": pn, "quantity": 1}], "ship_to_state": "GA"}
    wh = client.post("/api/quote", json=body, headers=headers(ids["warehouse"])).json()
    assert wh["ok"] and wh["options"]
    assert not _keys(wh) & SHIPPING_CHARGES
    assert all(o.get("carrier") and o.get("estimated_delivery_by") for o in wh["options"])
    cs = client.post("/api/quote", json=body, headers=headers(ids["cs"])).json()
    assert {"cost_usd", "customer_pays_usd"} <= _keys(cs)


def test_supervisor_analytics_hide_figures_derived_from_costs(client, ids):
    sup = _keys(client.get("/api/analytics", params={"period": "365"}, headers=headers(ids["cs_sup"])).json())
    assert not sup & DERIVED_COST
    director = _keys(client.get("/api/analytics", params={"period": "365"}, headers=headers(ids["director"])).json())
    assert DERIVED_COST <= director


# --------------------------------------------------------------------------- every field is classified (allowlist)
def test_field_groups_do_not_overlap():
    from app.auth import COST_FIELDS, CUSTOMER_FIELDS, MONEY_FIELDS, PUBLIC_FIELDS
    groups = [PUBLIC_FIELDS, COST_FIELDS, MONEY_FIELDS, CUSTOMER_FIELDS]
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            assert not a & b, a & b


def test_unclassified_fields_are_hidden_from_restricted_roles(ids):
    from app.auth import load_employee, redact
    data = {"part_number": "X1", "new_secret_margin": 12.5, "results": [{"order_id": "SO-1", "mystery": 1}]}
    for role in ("warehouse", "cs", "cs_sup"):
        assert redact(data, load_employee(ids[role])) == {"part_number": "X1", "results": [{"order_id": "SO-1"}]}
    assert redact(data, load_employee(ids["director"])) == data          # every permission: sees everything


def _all_field_names(client, ids):
    """Field names from every redacted endpoint and assistant tool, as a role that sees everything."""
    from app import assistant, db
    from app.auth import OPAQUE_FIELDS, load_employee
    found = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                found.add(k)
                if k not in OPAQUE_FIELDS:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    h = headers(ids["director"])
    old = db.scalar("SELECT part_number FROM parts WHERE status = 'Superseded' LIMIT 1")
    intl = db.scalar("SELECT order_id FROM orders WHERE order_type = 'International' AND status = 'Delivered' LIMIT 1")
    with_case = db.scalar("SELECT order_id FROM support_cases WHERE order_id IS NOT NULL LIMIT 1")
    for url, params in [("/api/inventory", {"limit": 5}), ("/api/inventory", {"stock_filter": "missing", "limit": 5}),
                        ("/api/parts/KV8Z-9402-Y", None), (f"/api/parts/{old}", None), ("/api/in-transit", None),
                        ("/api/orders", {"limit": 5}), (f"/api/orders/{intl}", None), (f"/api/orders/{with_case}", None),
                        ("/api/cases", None), ("/api/analytics", {"period": "all"})]:
        r = client.get(url, params=params, headers=h)
        assert r.status_code == 200, url
        walk(r.json())
    for body in ({"items": [{"part_number": "KV8Z-9402-Y"}], "ship_to_state": "FL"},
                 {"items": [{"part_number": "02938-T5C77"}], "ship_to_country": "CA", "customer_id": "R05016"},
                 {"items": [{"part_number": "KV8Z-9402-Y"}], "ship_to_country": "GB"}):
        walk(client.post("/api/quote", json=body, headers=h).json())
    od, sup = load_employee(ids["director"]), load_employee(ids["cs_sup"])
    cust = db.scalar("SELECT customer_id FROM customers WHERE customer_type = 'Individual' LIMIT 1")
    for emp, name, a in [(od, "search_inventory", {"q": "battery", "limit": 3}), (od, "get_part_details", {"part_number": old}),
                         (od, "find_in_transit", {}), (od, "search_orders", {"limit": 3}), (od, "get_order", {"order_id": intl}),
                         (od, "get_part_price", {"part_number": "KV8Z-9402-Y", "customer_id": "D0022"}),
                         (od, "get_part_price", {"part_number": old}),
                         (od, "quote_shipping", {"items": [{"part_number": "KV8Z-9402-Y"}], "ship_to_state": "FL"}),
                         (od, "full_quote", {"items": [{"part_number": "02938-T5C77"}], "customer_id": "R05016"}),
                         (od, "list_support_cases", {"status": "active", "limit": 3}), (od, "analytics_summary", {"period": "all"}),
                         (od, "search_faq", {"question": "return policy"}), (od, "contact_team", {"department_id": "RET"}),
                         (od, "escalate_to_person", {"question": "refund 400", "refund_amount_usd": 400}),
                         (sup, "propose_support_case", {"customer_id": cust, "department_id": "RET", "contact_reason": "x"})]:
        text, is_err = assistant.run_tool(emp, name, a)
        assert not is_err, (name, text[:200])
        walk(json.loads(text))
    return found


def test_every_returned_field_is_classified(client, ids):
    from app.auth import COST_FIELDS, CUSTOMER_FIELDS, MONEY_FIELDS, PUBLIC_FIELDS
    unclassified = _all_field_names(client, ids) - (PUBLIC_FIELDS | COST_FIELDS | MONEY_FIELDS | CUSTOMER_FIELDS)
    assert not unclassified, f"Classify these fields in app/auth.py: {sorted(unclassified)}"
