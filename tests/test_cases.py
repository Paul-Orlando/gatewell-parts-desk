"""The assistant only prepares support cases. A case is saved when the employee it was prepared for
clicks Create case, once, before the proposal expires."""
import json

from conftest import headers
from test_assistant import FakeModel

from app import assistant, db
from app.auth import load_employee


def _cases():
    return db.scalar("SELECT COUNT(*) FROM support_cases")


def _customer():
    return db.scalar("SELECT customer_id FROM customers WHERE customer_type = 'Individual' ORDER BY customer_id LIMIT 1")


def _propose(emp_id, **extra):
    text, is_err = assistant.run_tool(load_employee(emp_id), "propose_support_case",
                                      {"customer_id": _customer(), "department_id": "RET", "contact_reason": "Refund request", **extra})
    assert not is_err, text
    return json.loads(text)


def test_proposing_saves_nothing(ids):
    before = _cases()
    p = _propose(ids["cs"])
    assert _cases() == before
    assert p["proposal_id"] and p["department"] == "Returns & Cores" and "Not saved" in p["status"]


def test_chat_returns_the_pending_case(ids):
    fake = FakeModel([("tool", [("propose_support_case", {"customer_id": _customer(), "department_id": "RET",
                                                          "contact_reason": "Damaged part"})]),
                      ("text", "I've prepared the case. Check it and click Create case.")])
    before = _cases()
    out = assistant.chat(load_employee(ids["cs"]), [{"role": "user", "content": "open a returns case"}], client=fake)
    assert out["pending_case"]["contact_reason"] == "Damaged part" and _cases() == before


def test_confirm_creates_the_case_once(client, ids):
    p = _propose(ids["cs"])
    before = _cases()
    r = client.post("/api/cases/confirm", json={"proposal_id": p["proposal_id"]}, headers=headers(ids["cs"]))
    assert r.status_code == 200 and r.json()["case_id"].startswith("CS-")
    assert _cases() == before + 1
    again = client.post("/api/cases/confirm", json={"proposal_id": p["proposal_id"]}, headers=headers(ids["cs"]))
    assert again.status_code == 404 and _cases() == before + 1


def test_only_the_employee_it_was_prepared_for_can_confirm(client, ids):
    p = _propose(ids["cs"])
    other = db.scalar("SELECT employee_id FROM employees WHERE role = 'Customer Service Rep' AND employee_id <> ? LIMIT 1", ids["cs"])
    assert client.post("/api/cases/confirm", json={"proposal_id": p["proposal_id"]}, headers=headers(other)).status_code == 404
    assert client.post("/api/cases/confirm", json={"proposal_id": p["proposal_id"]}, headers=headers(ids["cs"])).status_code == 200


def test_roles_without_case_access_cannot_propose_or_confirm(client, ids):
    for role in ("warehouse", "director"):
        text, is_err = assistant.run_tool(load_employee(ids[role]), "propose_support_case",
                                          {"customer_id": _customer(), "department_id": "CS", "contact_reason": "x"})
        assert is_err and "isn't available" in text
    p = _propose(ids["cs"])
    assert client.post("/api/cases/confirm", json={"proposal_id": p["proposal_id"]}, headers=headers(ids["warehouse"])).status_code == 403


def test_expired_proposal_cannot_be_confirmed(client, ids):
    p = _propose(ids["cs"])
    assistant._pending_cases[p["proposal_id"]]["expires"] = 0
    assert client.post("/api/cases/confirm", json={"proposal_id": p["proposal_id"]}, headers=headers(ids["cs"])).status_code == 404


def test_proposal_checks_its_inputs(ids):
    text, is_err = assistant.run_tool(load_employee(ids["cs"]), "propose_support_case",
                                      {"customer_id": "NOPE", "department_id": "RET", "contact_reason": "x"})
    assert is_err and "No customer" in text
    text, is_err = assistant.run_tool(load_employee(ids["cs"]), "propose_support_case",
                                      {"customer_id": _customer(), "department_id": "XYZ", "contact_reason": "x"})
    assert is_err and "Unknown team" in text
