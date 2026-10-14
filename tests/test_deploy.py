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
