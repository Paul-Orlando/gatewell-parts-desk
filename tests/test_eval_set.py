"""The evaluation set (tests/eval/questions.yaml) stays honest: no model is called here.

Every source query or tool call is re-run against today's data, every listed value must be in its result, and
every expected fact must be backed by a source. A regenerated database that changes a number fails here, not
in a paid run of tests/eval/run_eval.py.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

from app import assistant, db
from app.auth import load_employee

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = yaml.safe_load((ROOT / "tests" / "eval" / "questions.yaml").read_text(encoding="utf-8"))
GROUPS = {"stock": 10, "orders": 6, "shipping": 8, "international": 6, "analytics": 6, "restricted": 8, "handoffs": 6}
FIELDS = {"id", "group", "employee_id", "expect_tools", "expect_handoff", "expect_refusal"}
DEPARTMENTS = {"RET", "BIL", "CS", "DLR", "EXP"}
REAL_NAME_QUESTIONS = {"stk-10", "shp-07"}          # use a real brand on purpose, to test the real-name rule


def _num(v):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _matches(want, got) -> bool:
    """A source value 'want' is in a result value 'got': equal numbers, or text contained (case-insensitive)."""
    a, b = _num(want), _num(got)
    if a is not None and b is not None:
        return abs(a - b) < 0.005
    return isinstance(got, str) and str(want).lower() in got.lower()


def _leaves(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _leaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from _leaves(v)
    else:
        yield o


def _run_source(src):
    if "sql" in src:
        assert src["sql"].lstrip().upper().startswith("SELECT"), "sources may only read"
        return [v for row in db.rows(src["sql"]) for v in row.values()]
    text, is_err = assistant.run_tool(load_employee(src["as"]), src["call"], src.get("args") or {})
    assert not is_err, text[:300]
    return list(_leaves(json.loads(text)))


def test_shape_and_group_counts():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids)) == 50
    assert {g: sum(q["group"] == g for q in QUESTIONS) for g in GROUPS} == GROUPS
    for q in QUESTIONS:
        assert FIELDS <= set(q), (q["id"], FIELDS - set(q))
        assert bool(q.get("question")) != bool(q.get("turns")), q["id"]
        assert q["expect_handoff"] is False or q["expect_handoff"] in DEPARTMENTS, q["id"]
        assert isinstance(q["expect_refusal"], bool), q["id"]
        if q.get("handoff_optional"):
            assert q["expect_handoff"] in DEPARTMENTS, f"{q['id']}: handoff_optional needs a department"
        if q.get("expect_facts"):
            assert q.get("sources"), f"{q['id']}: facts need a source"


def test_people_parts_orders_and_tools_exist():
    tools = assistant.TOOL_BY_NAME
    for q in QUESTIONS:
        emp = load_employee(q["employee_id"])
        assert emp, q["id"]
        for t in q["expect_tools"]:
            assert t in tools, (q["id"], t)
            assert tools[t]["roles"] == "all" or emp.role in tools[t]["roles"], (q["id"], t, emp.role)
        text = " ".join([q.get("question") or ""] + (q.get("turns") or []))
        for pn in re.findall(r"\b[A-Z]{2,3}-\d{5}[A-Z]?\b", text):
            assert db.scalar("SELECT 1 FROM parts WHERE part_number = ?", pn), (q["id"], pn)
        for oid in re.findall(r"\bSO-\d{6}\b", text):
            assert db.scalar("SELECT 1 FROM orders WHERE order_id = ?", oid), (q["id"], oid)
        for cid in re.findall(r"\b[DR]\d{4,5}\b", text):
            assert db.scalar("SELECT 1 FROM customers WHERE customer_id = ?", cid), (q["id"], cid)


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q.get("sources")], ids=lambda q: q["id"])
def test_sources_reproduce_every_value(q):
    for src in q["sources"]:
        got = _run_source(src)
        for want in src["gives"]:
            assert any(_matches(want, g) for g in got), f"{q['id']}: {want!r} not in {src.get('sql') or src['call']}"


@pytest.mark.parametrize("q", [q for q in QUESTIONS if q.get("expect_facts")], ids=lambda q: q["id"])
def test_every_fact_is_backed_by_a_source(q):
    gives = [g for src in q["sources"] for g in src["gives"]]
    for fact in q["expect_facts"]:
        options = fact if isinstance(fact, list) else [fact]
        assert any(_matches(o, g) or _matches(g, o) for o in options for g in gives if str(g)), \
            f"{q['id']}: {options} isn't backed by any source value"


def test_real_brand_names_only_where_intended():
    from tests.test_no_real_brands import DENY
    for q in QUESTIONS:
        text = " ".join([q.get("question") or ""] + (q.get("turns") or []))
        assert bool(DENY.search(text)) == (q["id"] in REAL_NAME_QUESTIONS), q["id"]
