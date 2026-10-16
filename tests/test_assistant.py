"""The assistant's tool loop, using a scripted stand-in for the model (no API key needed).

The stand-in speaks the same OpenAI-compatible format OpenRouter returns."""
import json

import pytest

from app import assistant
from app.auth import load_employee


class FakeModel:
    """Returns pre-scripted responses in order and records every request payload."""
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def complete(self, payload):
        self.calls.append(json.loads(json.dumps(payload)))       # snapshot, the loop keeps appending
        kind, value = self.script.pop(0)
        if kind == "tool":
            calls = [{"id": f"call_{i}", "type": "function",
                      "function": {"name": n, "arguments": a if isinstance(a, str) else json.dumps(a)}}
                     for i, (n, a) in enumerate(value)]
            msg = {"role": "assistant", "content": None, "tool_calls": calls}
            return {"choices": [{"message": msg, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 100, "completion_tokens": 10}}
        return {"choices": [{"message": {"role": "assistant", "content": value}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 20}}


def _tool_messages(payload):
    return [m for m in payload["messages"] if m["role"] == "tool"]


def test_tool_loop_runs_tools_and_redacts(ids):
    emp = load_employee(ids["warehouse"])
    fake = FakeModel([("tool", [("search_inventory", {"year": 2019, "make": "Ferra Motors", "model": "Nivo", "q": "brake pads"})]),
                      ("text", "Yes - we have them.")])
    out = assistant.chat(emp, [{"role": "user", "content": "Brake pads for a 2019 Nivo?"}], client=fake)
    assert out["reply"] == "Yes - we have them."
    assert out["tools_used"][0]["tool"] == "search_inventory" and out["tools_used"][0]["ok"]
    result = json.loads(_tool_messages(fake.calls[1])[0]["content"])
    assert result["count"] > 0
    assert "unit_cost_usd" not in result["results"][0]                  # warehouse role: costs removed
    first = fake.calls[0]
    assert first["messages"][0]["role"] == "system" and "Warehouse" in first["messages"][0]["content"]


def test_request_settings(ids):
    fake = FakeModel([("text", "ok")])
    assistant.chat(load_employee(ids["cs"]), [{"role": "user", "content": "hi"}], client=fake)
    p = fake.calls[0]
    assert p["model"] == assistant.MODEL == "google/gemini-3.1-flash-lite"
    assert p["provider"] == {"require_parameters": True}
    assert p["temperature"] <= 0.2 and p["tool_choice"] == "auto"
    names = {t["function"]["name"] for t in p["tools"]}
    assert "full_quote" in names and "analytics_summary" not in names


def test_role_only_gets_its_tools(ids):
    wh = {t["name"] for t in assistant.tools_for(load_employee(ids["warehouse"]))}
    cs = {t["name"] for t in assistant.tools_for(load_employee(ids["cs"]))}
    mgr = {t["name"] for t in assistant.tools_for(load_employee(ids["director"]))}
    assert "full_quote" not in wh and "analytics_summary" not in wh and "propose_support_case" not in wh
    assert "full_quote" in cs and "propose_support_case" in cs and "analytics_summary" not in cs
    assert "analytics_summary" in mgr and "propose_support_case" not in mgr


def test_blocked_tool_call_is_refused(ids):
    emp = load_employee(ids["warehouse"])
    text, is_err = assistant.run_tool(emp, "analytics_summary", {})
    assert is_err and "isn't available" in text
    # and if the model asks for it anyway, the loop refuses and carries on
    fake = FakeModel([("tool", [("analytics_summary", {})]), ("text", "I can't show analytics for your role.")])
    out = assistant.chat(emp, [{"role": "user", "content": "show analytics"}], client=fake)
    assert out["tools_used"][0]["ok"] is False and "isn't available" in _tool_messages(fake.calls[1])[0]["content"]


def test_bad_tool_arguments_are_handled(ids):
    fake = FakeModel([("tool", [("search_inventory", "{not json")]), ("text", "Let me try again.")])
    out = assistant.chat(load_employee(ids["cs"]), [{"role": "user", "content": "x"}], client=fake)
    assert out["tools_used"][0]["ok"] is False and out["reply"] == "Let me try again."


def test_escalation_returns_contact_and_faq(ids):
    emp = load_employee(ids["cs"])
    fake = FakeModel([("tool", [("escalate_to_person", {"question": "Customer wants a $400 refund on a radiator", "refund_amount_usd": 400})]),
                      ("text", "I've routed this to Returns & Cores.")])
    out = assistant.chat(emp, [{"role": "user", "content": "Customer wants a $400 refund"}], client=fake)
    h = out["handoff"]
    assert h["handoff"] and h["department_id"] == "RET"
    assert h["contact"]["phone"] and h["contact"]["faq_page"].endswith("/faq")


def test_loop_stops_after_max_rounds(ids):
    emp = load_employee(ids["cs"])
    fake = FakeModel([("tool", [("search_faq", {"question": "returns"})])] * assistant.MAX_TOOL_ROUNDS)
    out = assistant.chat(emp, [{"role": "user", "content": "loop"}], client=fake)
    assert "couldn't finish" in out["reply"]
    assert len(fake.calls) == assistant.MAX_TOOL_ROUNDS


def test_audit_log_written(ids, tmp_dir):
    emp = load_employee(ids["cs"])
    assistant.chat(emp, [{"role": "user", "content": "audit me"}], client=FakeModel([("text", "ok")]))
    entry = json.loads((tmp_dir / "logs" / "assistant_audit.jsonl").read_text().strip().splitlines()[-1])
    assert entry["question"] == "audit me" and entry["model"] == assistant.MODEL and entry["tokens"]["prompt_tokens"] == 120


def test_chat_endpoint_without_api_key(client, ids):
    from conftest import headers
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]}, headers=headers(ids["cs"])).json()
    assert r["unavailable"] and "OPENROUTER_API_KEY" in r["reply"]


def test_openrouter_errors_become_friendly_message(monkeypatch):
    import httpx

    class Resp:
        status_code, headers = 401, {"content-type": "application/json"}
        def json(self): return {"error": {"message": "Invalid API key"}}
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append(1) or Resp())
    with pytest.raises(assistant.AssistantUnavailable) as e:
        assistant.OpenRouterClient("bad-key").complete({"model": "x", "messages": []})
    assert "Invalid API key" in str(e.value) and "(800) 555-0142" in str(e.value)
    assert len(calls) == 1                                   # client errors aren't retried


def test_openrouter_server_errors_retry_once(monkeypatch):
    import httpx

    class Resp:
        status_code, headers = 503, {"content-type": "text/plain"}
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append(1) or Resp())
    monkeypatch.setattr(assistant.time, "sleep", lambda s: None)
    with pytest.raises(assistant.AssistantUnavailable):
        assistant.OpenRouterClient("k").complete({})
    assert len(calls) == 2


# --------------------------------------------------------------------------- live test 2026-10-14 fixes
def test_every_warehouse_parameter_is_an_enum_of_the_real_codes():
    from app import db
    codes = [r["warehouse_code"] for r in db.rows("SELECT warehouse_code FROM warehouses ORDER BY warehouse_code")]
    with_wh = {t["name"]: t["schema"]["properties"]["warehouse"] for t in assistant.TOOLS
               if "warehouse" in t["schema"].get("properties", {})}
    assert set(with_wh) == {"search_inventory", "find_in_transit", "search_orders", "analytics_summary", "recommend_actions"}
    assert all(p["enum"] == codes for p in with_wh.values())


def test_prompt_lists_every_warehouse_code(ids):
    from app import db
    prompt = assistant.system_prompt(load_employee(ids["director"]))
    for code in (r["warehouse_code"] for r in db.rows("SELECT warehouse_code FROM warehouses")):
        assert f" {code} " in prompt
    assert "ORD Chicago" in prompt and "LAX Inland Empire (Ontario, CA, also Los Angeles)" in prompt


def test_guessed_warehouse_code_is_rejected_with_the_valid_list(ids):
    text, is_err = assistant.run_tool(load_employee(ids["director"]), "analytics_summary", {"warehouse": "CHI", "sections": ["kpis"]})
    assert is_err and "Unknown warehouse 'CHI'" in text and "ORD (Chicago, IL)" in text


def test_prompt_rules_from_the_live_test(ids):
    p = {role: assistant.system_prompt(load_employee(ids[role])) for role in ("cs", "cs_sup", "warehouse", "director")}
    for text in p.values():
        assert "You are talking to an employee, not the customer" in text and "You can tell the customer" in text   # B
        assert "list the options before quoting one, or ask which one" in text                                    # A
        assert "look up what they can see about the\n  same thing and include it" in text                               # D
        assert "Prefer one broad lookup over many narrow ones" in text and "request them together" in text          # G
    offer = "Want me to open a support case?"                                                                       # C
    assert offer in p["cs"] and offer in p["cs_sup"]
    assert offer not in p["warehouse"] and offer not in p["director"]


def test_prompt_rules_from_the_retest(ids):
    for role in ("cs", "cs_sup", "warehouse", "director"):
        text = assistant.system_prompt(load_employee(ids[role]))
        assert "Never mention tool names, section names, field names" in text                     # 1: no internal names
        assert "State tax, duty and policy details exactly as the tools give them" in text        # 2: no added details
        assert "look that part up for that warehouse" in text                                     # 3: drill into the warehouse
    assert "has a note saying how many days late" in assistant.TOOL_BY_NAME["find_in_transit"]["description"]


def test_prompt_asks_which_of_our_names_when_a_real_one_is_used(ids):
    """Post-rename: a real make, model or carrier is never treated as one of ours; the assistant lists ours and asks."""
    from tests.test_no_real_brands import M
    for role in ("cs", "cs_sup", "warehouse", "director"):
        text = assistant.system_prompt(load_employee(ids[role]))
        assert "say our\n  catalog doesn't carry that name, list our makes (or carriers), and ask which one they mean" in text
        assert "Never treat an\n  outside name as equal to one of ours" in text
        listed = text[text.index("Our catalog uses its own vehicle makes"):text.index("If the employee names a make")]
        assert all(make in listed for make in M.FICTIONAL_MAKES)
        assert all(carrier in listed for carrier in M.FICTIONAL_CARRIERS)


def test_escalation_says_who_is_needed_and_that_nothing_was_sent(ids):
    for role, step in (("cs", "Not yet sent. Offer to open a support case."),
                       ("warehouse", "Not yet sent. The employee can contact the team directly.")):
        text, is_err = assistant.run_tool(load_employee(ids[role]), "escalate_to_person",
                                          {"question": "customer wants a $400 refund", "refund_amount_usd": 400})
        d = json.loads(text)
        assert not is_err and d["next_step"] == step and d["case_status"] == step
        assert "This needs the Returns & Cores team" in d["message_to_customer"] and "Queued" not in text
        prompt = assistant.system_prompt(load_employee(ids[role]))
        assert 'Say "This needs the [team] team"' in prompt and "Never say you escalated, passed on" in prompt
        assert "A support case exists only after the employee clicks Create case" in prompt


def test_analytics_labels_stock_as_point_in_time(ids):
    text, _ = assistant.run_tool(load_employee(ids["director"]), "analytics_summary",
                                 {"period": "90", "sections": ["missing_by_warehouse_group", "inventory_by_warehouse", "top_parts"]})
    d = json.loads(text)
    notes = d["section_notes"]
    assert set(notes) == {"missing_by_warehouse_group", "missing_by_warehouse", "inventory_by_warehouse", "top_parts", "kpis"}
    for s in ("missing_by_warehouse_group", "missing_by_warehouse", "inventory_by_warehouse"):
        assert notes[s].startswith("Point in time, as of ") and "90 days" not in notes[s]
        assert d["stock_as_of"] in notes[s]
    assert "never describe them as 'last N days'" in d["how_to_read"]
    assert "last 90 days" in notes["top_parts"] and "last 90 days" in d["period_covers"]
    stock, sales = notes["kpis"].split("Orders, revenue")
    assert "as of" in stock and "90 days" not in stock and "last 90 days" in sales
    assert "Stock counts (on hand, available, in transit, missing, low stock) are point in time" in         assistant.system_prompt(load_employee(ids["director"]))


def _missing_by_warehouse_sql(codes=None):
    from app import db
    where = f"AND i.warehouse_code IN ({','.join('?' * len(codes))})" if codes else ""
    return {r["warehouse_code"]: (r["units"], r["value"]) for r in db.rows(
        f"""SELECT i.warehouse_code, SUM(i.qty_missing) units, ROUND(SUM(i.qty_missing * i.unit_cost_usd)) value
            FROM inventory i WHERE i.qty_missing > 0 {where} GROUP BY 1""", *(codes or []))}


def test_warehouse_missing_totals_come_from_the_tool_and_match_the_database(ids):
    """Retest 2026-10-16: the model added up category rows (NWK $4,921, ATL 13 units / $868). The tool now gives
    exact per-warehouse totals next to the breakdown, so there's nothing to add."""
    d = json.loads(assistant.run_tool(load_employee(ids["director"]), "analytics_summary",
                                      {"sections": ["missing_by_warehouse_group"]})[0])
    got = {r["label"]: (r["units_missing"], r["missing_value_usd"]) for r in d["missing_by_warehouse"]}
    assert got == _missing_by_warehouse_sql()
    assert got["NWK"] == (140, 4951) and got["ATL"] == (12, 866)
    assert d["missing_by_warehouse"][0]["label"] == "NWK"                        # largest first
    total = d["section_totals"]["missing_by_warehouse_group"]
    assert (total["units"], total["missing_value_usd"]) == (d["kpis"]["units_missing"], d["kpis"]["missing_value_usd"])
    assert d["section_totals"]["missing_by_warehouse"]["units_missing"] == sum(u for u, _ in got.values())


def test_section_totals_stay_in_scope_and_match_the_database(ids):
    from app import db
    reg = load_employee(ids["regional"])
    d = json.loads(assistant.run_tool(reg, "analytics_summary", {"period": "90", "sections": [
        "missing_by_warehouse", "sales_by_group", "revenue_by_region"]})[0])
    mine = sorted(reg.warehouses())
    assert {r["label"] for r in d["missing_by_warehouse"]} <= set(mine)
    assert {r["label"]: (r["units_missing"], r["missing_value_usd"]) for r in d["missing_by_warehouse"]} == \
        _missing_by_warehouse_sql(mine)
    start = (db.as_of() - __import__("datetime").timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ph = ",".join("?" * len(mine))
    sales = db.one(f"""SELECT SUM(ol.quantity) units, ROUND(SUM(ol.line_total_usd)) revenue_usd
                       FROM order_lines ol JOIN orders o USING (order_id)
                       WHERE ol.line_status IN ('Shipped','Delivered','Returned') AND o.ordered_at_utc >= ?
                       AND o.fulfillment_warehouse IN ({ph})""", start, *mine)
    assert d["section_totals"]["sales_by_group"] == sales
    region = db.one(f"""SELECT COUNT(*) orders, ROUND(SUM(order_total_usd)) revenue_usd FROM orders o
                        WHERE status <> 'Cancelled' AND ordered_at_utc >= ? AND fulfillment_warehouse IN ({ph})""", start, *mine)
    assert d["section_totals"]["revenue_by_region"] == region


def test_prompt_forbids_model_arithmetic(ids):
    for role in ("cs", "cs_sup", "warehouse", "director"):
        text = assistant.system_prompt(load_employee(ids[role]))
        assert "Never add, subtract or average figures yourself. Report totals and figures exactly as the tools return" in text
        assert "If\n  you need a total the tool didn't return, call the section that has it" in text


def test_as_of_times_are_shown_in_central(ids, client):
    """As-of times reach the model and the screens as "Sun, Oct 11, 4:00 PM Central", never in UTC."""
    from datetime import datetime, timezone
    from app import dates
    from tests.conftest import headers
    central = "Sun, Oct 11, 4:00 PM Central"
    assert dates.as_of_central() == central
    assert dates.as_of_central(datetime(2026, 1, 15, 21, 0, tzinfo=timezone.utc)) == "Thu, Jan 15, 3:00 PM Central"   # CST
    for role in ("director", "cs_sup"):                       # cs_sup: a restricted role, so redaction must keep it
        d = json.loads(assistant.run_tool(load_employee(ids[role]), "analytics_summary",
                                          {"period": "90", "sections": ["missing_by_group", "top_parts"]})[0])
        assert d["as_of_display"] == d["stock_as_of"] == central
        assert all(central in n for k, n in d["section_notes"].items() if k != "top_parts")
        assert not any("UTC" in n for n in d["section_notes"].values())
        prompt = assistant.system_prompt(load_employee(ids[role]))
        data_line = next(line for line in prompt.splitlines() if line.startswith("Data is current as of"))
        assert central in data_line and "UTC" not in data_line
        assert "Give as-of times in Central" in prompt
        assert "When a customer name isn't found, search once more at most" in prompt
    for role in ("director", "cs_sup"):
        h = headers(ids[role])
        assert client.get("/api/me", headers=h).json()["as_of_display"] == central
        assert client.get("/api/analytics", headers=h).json()["as_of_display"] == central


def test_display_dates_follow_redaction(ids):
    from app import dates
    assert dates.display("2026-10-13") == "Tue, Oct 13"
    assert dates.display("2026-10-14T05:00-04:00") == "Wed, Oct 14, 5:00 AM"
    assert dates.display("2025-12-15") == "Mon, Dec 15, 2025"
    assert dates.display("2026-10-11T21:00:00Z") is None and dates.display("SO-000123") is None
    q = json.loads(assistant.run_tool(load_employee(ids["cs"]), "quote_shipping",
                                      {"items": [{"part_number": "HL-100214"}], "ship_to_state": "TX"})[0])
    assert q["options"][0]["estimated_delivery_by_display"] == dates.display(q["options"][0]["estimated_delivery_by"])

    def pairs(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.endswith("_display"):
                    assert k[:-len("_display")] in o, k          # never a display value without its visible source
                pairs(v)
        elif isinstance(o, list):
            for v in o:
                pairs(v)
    for role in ("warehouse", "cs"):
        emp = load_employee(ids[role])
        for name, a in (("search_orders", {"limit": 5}), ("find_in_transit", {}), ("get_part_details", {"part_number": "IH-100009"}),
                        ("recommend_actions", {"part_number": "IH-100009", "warehouse": "ATL"})):
            text, is_err = assistant.run_tool(emp, name, a)
            assert not is_err, (role, name, text[:200])
            pairs(json.loads(text))
    assert 'Write dates the way the *_display values give them' in assistant.system_prompt(load_employee(ids["cs"]))


def test_prompt_examples_use_plain_words(ids):
    """Step 3: worked examples for asking the engine, listing options, taxed totals and handoffs, with no tool,
    section or data values in them (the numbers must come from lookups, not from the prompt)."""
    from app import analytics
    for role in ("cs", "warehouse", "director"):
        text = assistant.system_prompt(load_employee(ids[role]))
        ex = text[text.index("Examples of good answers"):text.index("Access rules")]
        assert "Which engine does it have" in ex and "list both" in ex and "full quote" in ex and "$250" in ex
        assert not any(name in ex for name in [t["name"] for t in assistant.TOOLS] + list(analytics.SECTIONS))
        assert ("open a support case" in ex) == (role == "cs")
