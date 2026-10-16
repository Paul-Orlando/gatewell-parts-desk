"""The demo version allows 5 assistant questions per visitor, counted on the server."""
import pytest
from fastapi.testclient import TestClient

from app import assistant
from app.server import app
from conftest import headers


class AlwaysAnswers:
    """Stand-in for the model that answers every question with plain text."""
    def complete(self, payload):
        return {"choices": [{"message": {"role": "assistant", "content": "Answer."}, "finish_reason": "stop"}]}


@pytest.fixture
def demo_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GATEWELL_DEMO_MODE", "1")
    monkeypatch.setenv("GATEWELL_DEMO_CHAT_LIMIT", "5")
    monkeypatch.setenv("GATEWELL_DEMO_IP_LIMIT", "25")
    monkeypatch.setenv("GATEWELL_DEMO_DB", str(tmp_path / "demo.db"))
    monkeypatch.setattr(assistant, "_get_client", lambda: AlwaysAnswers())
    return monkeypatch


def ask(c, emp, text="Do we have brake pads?"):
    return c.post("/api/chat", json={"messages": [{"role": "user", "content": text}]}, headers=headers(emp))


def test_five_questions_then_blocked(demo_env, ids):
    c = TestClient(app)
    left = [ask(c, ids["cs"]).json()["demo"]["remaining"] for _ in range(5)]
    assert left == [4, 3, 2, 1, 0]
    r = ask(c, ids["cs"])
    assert r.status_code == 429
    assert "used all 5 questions" in r.json()["detail"]
    assert c.get("/api/demo-status", headers=headers(ids["cs"])).json()["remaining"] == 0


def test_switching_employee_does_not_reset(demo_env, ids):
    c = TestClient(app)
    for _ in range(3):
        ask(c, ids["cs"])
    for _ in range(2):
        ask(c, ids["warehouse"])
    assert ask(c, ids["director"]).status_code == 429


def test_unanswered_requests_do_not_count(demo_env, ids):
    def unavailable():
        raise assistant.AssistantUnavailable("off")
    demo_env.setattr(assistant, "_get_client", unavailable)
    c = TestClient(app)
    for _ in range(7):
        assert ask(c, ids["cs"]).json()["unavailable"]
    assert c.get("/api/demo-status", headers=headers(ids["cs"])).json()["remaining"] == 5


def test_network_backstop_stops_cookie_resets(demo_env, ids):
    demo_env.setenv("GATEWELL_DEMO_IP_LIMIT", "7")
    first = TestClient(app)
    for _ in range(5):
        ask(first, ids["cs"])
    second = TestClient(app)                     # a new visitor (no cookie) from the same address
    assert [ask(second, ids["cs"]).status_code for _ in range(3)] == [200, 200, 429]


def test_demo_mode_off_has_no_limit(demo_env, ids):
    demo_env.setenv("GATEWELL_DEMO_MODE", "0")
    c = TestClient(app)
    assert all(ask(c, ids["cs"]).status_code == 200 for _ in range(7))
    assert c.get("/api/demo-status", headers=headers(ids["cs"])).json() == {"enabled": False}


class NeverFinishes:
    """Stand-in model that keeps asking for another lookup, so every question hits the tool-round limit."""
    def complete(self, payload):
        call = {"id": "c1", "type": "function", "function": {"name": "search_faq", "arguments": '{"question": "returns"}'}}
        return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [call]}}]}


def test_reply_cut_off_by_the_round_limit_does_not_count(demo_env, ids):
    demo_env.setattr(assistant, "_get_client", lambda: NeverFinishes())
    c = TestClient(app)
    r = ask(c, ids["cs"]).json()
    assert "couldn't finish" in r["reply"] and r["finished"] is False
    assert r["demo"]["remaining"] == 5
    demo_env.setattr(assistant, "_get_client", lambda: AlwaysAnswers())
    assert ask(c, ids["cs"]).json()["demo"]["remaining"] == 4          # a finished answer still counts


# ---------------------------------------------------------------- support case limits (the app's only write)
from test_cases import _cases, _propose      # noqa: E402


def confirm(c, emp, proposal_id):
    return c.post("/api/cases/confirm", json={"proposal_id": proposal_id}, headers=headers(emp))


@pytest.fixture
def case_env(demo_env):
    demo_env.setenv("GATEWELL_DEMO_CASE_LIMIT", "3")
    demo_env.setenv("GATEWELL_DEMO_CASES_PER_DAY", "50")
    return demo_env


def test_three_cases_per_visitor_then_blocked(case_env, ids):
    c, before = TestClient(app), _cases()
    assert [confirm(c, ids["cs"], _propose(ids["cs"])["proposal_id"]).status_code for _ in range(3)] == [200] * 3
    r = confirm(c, ids["cs"], _propose(ids["cs"])["proposal_id"])
    assert r.status_code == 429 and "3 support cases per visitor" in r.json()["detail"]
    assert _cases() == before + 3                                      # the blocked one saved nothing
    assert confirm(TestClient(app), ids["cs"], _propose(ids["cs"])["proposal_id"]).status_code == 200   # a new visitor can


def test_daily_cap_blocks_every_visitor(case_env, ids):
    case_env.setenv("GATEWELL_DEMO_CASES_PER_DAY", "2")
    for _ in range(2):
        assert confirm(TestClient(app), ids["cs"], _propose(ids["cs"])["proposal_id"]).status_code == 200
    r = confirm(TestClient(app), ids["cs"], _propose(ids["cs"])["proposal_id"])     # fresh cookie: still blocked
    assert r.status_code == 429 and "today's limit of 2 support cases" in r.json()["detail"]


def test_failed_confirm_does_not_use_a_case(case_env, ids):
    c = TestClient(app)
    for _ in range(5):
        assert confirm(c, ids["cs"], "no-such-proposal").status_code == 404
    assert [confirm(c, ids["cs"], _propose(ids["cs"])["proposal_id"]).status_code for _ in range(3)] == [200] * 3


def test_case_limit_comes_after_the_role_check(case_env, ids):
    case_env.setenv("GATEWELL_DEMO_CASES_PER_DAY", "0")               # every case would be blocked
    p = _propose(ids["cs"])
    assert confirm(TestClient(app), ids["warehouse"], p["proposal_id"]).status_code == 403
    assert TestClient(app).post("/api/cases/confirm", json={"proposal_id": p["proposal_id"]}).status_code == 401


def test_case_limit_off_only_with_demo_mode_0(case_env, ids):
    case_env.setenv("GATEWELL_DEMO_CASE_LIMIT", "0")
    c = TestClient(app)
    assert confirm(c, ids["cs"], _propose(ids["cs"])["proposal_id"]).status_code == 429
    case_env.setenv("GATEWELL_DEMO_MODE", "0")
    assert confirm(c, ids["cs"], _propose(ids["cs"])["proposal_id"]).status_code == 200


@pytest.mark.parametrize("value", [None, "", "  ", "1", "yes"])
def test_demo_mode_stays_on_unless_switched_off(demo_env, value):
    """A missing or empty variable can't turn the limits off; only 0/false/no/off does."""
    from app import demo
    if value is None:
        demo_env.delenv("GATEWELL_DEMO_MODE", raising=False)
    else:
        demo_env.setenv("GATEWELL_DEMO_MODE", value)
    assert demo.enabled()
    for off in ("0", "false", "No", "OFF"):
        demo_env.setenv("GATEWELL_DEMO_MODE", off)
        assert not demo.enabled()
