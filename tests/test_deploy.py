"""Things Railway relies on: health check, security headers, first-start database copy."""
import shutil

from app import db


def test_health_check_needs_no_sign_in(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_security_headers(client):
    h = client.get("/").headers
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"


def test_database_copied_to_empty_volume(tmp_path, monkeypatch):
    target = tmp_path / "volume" / "car_parts_inventory.db"
    monkeypatch.setattr(db, "DB_PATH", str(target))
    db.ensure_database()
    assert target.exists() and target.stat().st_size == db.BUNDLED_DB.stat().st_size
    target.write_bytes(b"existing")                     # never overwrite a database that's already there
    db.ensure_database()
    assert target.read_bytes() == b"existing"


def test_health_check_fails_when_the_database_cant_be_read(client, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("database missing")
    monkeypatch.setattr(db, "scalar", broken)
    r = client.get("/api/health")
    assert r.status_code == 503 and r.json() == {"ok": False}


def test_log_folders_are_created_on_first_use(tmp_path, monkeypatch):
    """GATEWELL_LOG_DIR=/data/logs doesn't exist on a fresh volume: the audit log and demo counts create it."""
    from app import assistant, demo
    logs = tmp_path / "volume" / "logs"
    monkeypatch.setattr(assistant, "LOG_DIR", logs)
    assistant._audit({"at": "test"})
    assert (logs / "assistant_audit.jsonl").exists()
    monkeypatch.setenv("GATEWELL_LOG_DIR", str(tmp_path / "volume2" / "logs"))
    monkeypatch.delenv("GATEWELL_DEMO_DB", raising=False)
    demo.record("visitor", "1.2.3.4")
    assert (tmp_path / "volume2" / "logs" / "demo_usage.db").exists()


def test_sign_in_page_says_questions_are_logged(client):
    assert "Demo questions are logged to improve the app. Don't enter personal information." in client.get("/").text
