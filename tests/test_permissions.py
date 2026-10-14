"""Each role sees only what it should, and data scope limits warehouses - enforced by the server."""
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
