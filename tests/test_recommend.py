"""Suggested actions (app/recommend.py): read-only, scoped to the employee's warehouses, cost estimates redacted."""
import json

from conftest import headers

from app import assistant, db, recommend
from app.auth import load_employee


def test_backordered_part_covered_by_inbound_gets_no_reorder(client, ids):
    r = client.get("/api/parts/68253600AW/suggestions", headers=headers(ids["wh_manager"])).json()
    assert r["for_warehouse"] == "ATL" and r["qty_backordered"] == 11 and r["qty_in_transit"] == 120
    assert r["reorder"]["covered_by_inbound"] is True and r["reorder"]["suggested_qty"] == 0
    assert r["reorder"]["quantity"] == 120 and r["reorder"]["next_eta_local"].startswith("2026-10-14")
    assert "120 arrive 2026-10-14 by air" in r["summary"] and "no reorder is needed" in r["summary"]
    assert r["suggestion"] == "Covered by inbound 120" and r["label"] == recommend.LABEL


def test_transfers_never_take_a_source_below_its_reorder_point(ids):
    od = load_employee(ids["director"])
    for row in recommend.recommend_for_warehouse(od)["recommendations"]:
        r = recommend.recommend_for_part(od, row["part_number"], row["warehouse_code"])
        for t in r["transfer_options"]:
            s = db.one("SELECT qty_available, reorder_point FROM v_stock_position WHERE part_number = ? AND warehouse_code = ?",
                       r["part_number"], t["warehouse_code"])
            assert t["warehouse_code"] != r["for_warehouse"]
            assert 0 < t["suggested_qty"] <= t["spare_qty"] == s["qty_available"] - s["reorder_point"]
            assert s["qty_available"] - t["suggested_qty"] >= s["reorder_point"]
            assert t["suggested_qty"] <= r["need_now"]


def test_suggestions_only_for_warehouses_in_scope(client, ids):
    r = client.get("/api/parts/68253600AW/suggestions", params={"warehouse": "NWK"}, headers=headers(ids["wh_manager"]))
    assert r.status_code == 400 and "outside your view" in r.json()["detail"]
    text, is_err = assistant.run_tool(load_employee(ids["wh_manager"]), "recommend_actions", {"warehouse": "NWK"})
    assert is_err and "outside your view" in text
    regional = load_employee(ids["regional"])                    # Northeast: NWK only; sources may be anywhere
    rows = recommend.recommend_for_warehouse(regional)["recommendations"]
    assert rows and {r["warehouse_code"] for r in rows} <= set(regional.warehouses())


def test_shipping_cost_is_hidden_from_roles_without_costs(client, ids):
    url = "/api/parts/08294-PAK-H95/suggestions"
    mgr = client.get(url, params={"warehouse": "NWK"}, headers=headers(ids["director"])).json()
    assert mgr["transfer_options"] and all("estimated_cost_usd" in t for t in mgr["transfer_options"])
    assert "about $" in mgr["summary"]
    for role in ("cs", "cs_sup", "warehouse"):
        params = {"warehouse": "NWK"} if role != "warehouse" else None
        r = client.get(url if role != "warehouse" else "/api/parts/68253600AW/suggestions", params=params,
                       headers=headers(ids[role])).json()
        assert all("estimated_cost_usd" not in t for t in r["transfer_options"]) and "$" not in r["summary"], role
        if role != "warehouse":
            assert r["transfer_options"] and all("transit_days" in t for t in r["transfer_options"])


def test_warehouse_roles_get_no_reorder(client, ids):
    r = client.get("/api/parts/68253600AW/suggestions", headers=headers(ids["warehouse"])).json()
    assert r["for_warehouse"] == "ATL" and "reorder" not in r and r["substitutes"]
    assert "reorder" not in r["suggestion"].lower() or "Covered" in r["suggestion"]


def test_suggestions_change_nothing(client, ids):
    tables = [t["name"] for t in db.rows("SELECT name FROM sqlite_master WHERE type = 'table'")]
    before = {t: db.scalar(f'SELECT COUNT(*) FROM "{t}"') for t in tables}
    od = load_employee(ids["director"])
    recommend.recommend_for_warehouse(od)
    for pn, wh in (("68253600AW", "ATL"), ("08294-PAK-H95", "NWK"), ("50712-XAV-D58", "NWK")):
        client.get(f"/api/parts/{pn}/suggestions", params={"warehouse": wh}, headers=headers(ids["director"]))
        assistant.run_tool(od, "recommend_actions", {"part_number": pn, "warehouse": wh})
    client.get("/api/analytics", headers=headers(ids["director"]))
    assert before == {t: db.scalar(f'SELECT COUNT(*) FROM "{t}"') for t in tables}


def test_recommend_tool_roles_and_results(ids):
    t = assistant.TOOL_BY_NAME["recommend_actions"]
    assert t["roles"] == "all"                         # every role; the reorder section is removed for warehouse roles
    for role in ("warehouse", "cs", "cs_sup", "director"):
        assert "recommend_actions" in [x["name"] for x in assistant.tools_for(load_employee(ids[role]))]
    out = json.loads(assistant.run_tool(load_employee(ids["director"]), "recommend_actions",
                                        {"warehouse": "NWK", "category": "Sensors"})[0])
    assert out["recommendations"] and all(r["warehouse_code"] == "NWK" and r["suggestion"] for r in out["recommendations"])
    assert "Never say an action has been taken" in assistant.system_prompt(load_employee(ids["cs"]))


def test_analytics_low_stock_has_a_suggestion(client, ids):
    d = client.get("/api/analytics", params={"warehouse": "NWK"}, headers=headers(ids["director"])).json()
    assert d["low_stock"] and all(r["suggestion"] for r in d["low_stock"])
