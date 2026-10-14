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
