"""
Demo limit for the assistant.

In the demo version, each visitor can ask the assistant a fixed number of questions
(default 5). The count is kept on the server, keyed by a visitor cookie the server sets,
so reloading the page or switching to another sample employee doesn't reset it. A second,
higher limit per network address stops someone from resetting it by clearing cookies.

Only answered questions count: a request that fails, finds the assistant switched off, or
ends with "I couldn't finish looking that up" (the tool-round limit) doesn't use up a question.

Settings (environment variables):
    GATEWELL_DEMO_MODE        1 = demo limits on (default), 0 = off
    GATEWELL_DEMO_CHAT_LIMIT  questions per visitor (default 5)
    GATEWELL_DEMO_IP_LIMIT    questions per network address (default 25, allows a few
                              people demoing from the same office)
    GATEWELL_DEMO_DB          where the counts are stored (default logs/demo_usage.db)
"""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COOKIE = "gw_demo"


def enabled() -> bool:
    return os.environ.get("GATEWELL_DEMO_MODE", "1").strip().lower() not in ("0", "false", "no", "off")


def limit() -> int:
    return int(os.environ.get("GATEWELL_DEMO_CHAT_LIMIT", "5"))


def ip_limit() -> int:
    return int(os.environ.get("GATEWELL_DEMO_IP_LIMIT", "25"))


def _db_path() -> str:
    default = Path(os.environ.get("GATEWELL_LOG_DIR", ROOT / "logs")) / "demo_usage.db"
    p = Path(os.environ.get("GATEWELL_DEMO_DB", default))
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


_lock = threading.Lock()


def _con():
    con = sqlite3.connect(_db_path())
    con.execute("""CREATE TABLE IF NOT EXISTS demo_usage (
                     usage_key TEXT PRIMARY KEY, questions INTEGER NOT NULL DEFAULT 0,
                     first_at TEXT, last_at TEXT)""")
    return con


def _used(con, key: str) -> int:
    r = con.execute("SELECT questions FROM demo_usage WHERE usage_key = ?", (key,)).fetchone()
    return r[0] if r else 0


def status(visitor: str, ip: str) -> dict:
    """How many demo questions this visitor has left."""
    if not enabled():
        return {"enabled": False}
    with _lock:
        con = _con()
        try:
            used_v, used_ip = _used(con, f"visitor:{visitor}"), _used(con, f"ip:{ip}")
        finally:
            con.close()
    remaining = max(0, min(limit() - used_v, ip_limit() - used_ip))
    return {"enabled": True, "limit": limit(), "used": min(used_v, limit()), "remaining": remaining}


def record(visitor: str, ip: str) -> None:
    """Count one answered question against the visitor and their network address."""
    if not enabled():
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _lock:
        con = _con()
        try:
            for key in (f"visitor:{visitor}", f"ip:{ip}"):
                con.execute("""INSERT INTO demo_usage (usage_key, questions, first_at, last_at) VALUES (?, 1, ?, ?)
                               ON CONFLICT(usage_key) DO UPDATE SET questions = questions + 1, last_at = excluded.last_at""",
                            (key, now, now))
            con.commit()
        finally:
            con.close()


def limit_message() -> str:
    return (f"You've used all {limit()} questions in this demo. The full version has no limit. "
            "You can keep using Inventory, Orders and the other tabs, read the FAQ at "
            "https://www.gatewellautoparts.example/faq, or call Customer Service at (800) 555-0142.")


def client_ip(request) -> str:
    """The visitor's address. Behind Railway's proxy the real one is the first X-Forwarded-For entry."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
