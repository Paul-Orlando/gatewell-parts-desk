"""
Database access for the Gatewell employee app.

Reads use a read-only SQLite connection, so nothing in the app (including the AI assistant)
can change inventory, orders or prices by accident. The only writes are support cases,
which go through a separate, narrowly scoped connection in write_support_case().
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("GATEWELL_DB", str(ROOT / "data" / "car_parts_inventory.db"))

BUNDLED_DB = ROOT / "data" / "car_parts_inventory.db"


def ensure_database() -> None:
    """On Railway the database lives on a volume (e.g. /data). On the first start the volume is empty,
    so copy the bundled sample database there. Never overwrites an existing database."""
    target = Path(DB_PATH)
    if not target.exists() and BUNDLED_DB.exists() and target.resolve() != BUNDLED_DB.resolve():
        import shutil
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(BUNDLED_DB, target)


ensure_database()

# The sample data is a snapshot taken at this moment. With live data, set GATEWELL_AS_OF=now.
_AS_OF = os.environ.get("GATEWELL_AS_OF", "2026-10-11T21:00:00Z")


def as_of() -> datetime:
    if _AS_OF.lower() == "now":
        return datetime.now(timezone.utc)
    return datetime.strptime(_AS_OF, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def read_conn() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def rows(sql: str, *args) -> list[dict]:
    con = read_conn()
    try:
        return [dict(r) for r in con.execute(sql, args).fetchall()]
    finally:
        con.close()


def one(sql: str, *args) -> dict | None:
    r = rows(sql, *args)
    return r[0] if r else None


def scalar(sql: str, *args):
    con = read_conn()
    try:
        r = con.execute(sql, args).fetchone()
        return r[0] if r else None
    finally:
        con.close()


def write_support_case(row: dict) -> None:
    """The app's only write path: insert one support case."""
    con = sqlite3.connect(DB_PATH)
    try:
        cols = ",".join(row)
        con.execute(f"INSERT INTO support_cases ({cols}) VALUES ({','.join('?' * len(row))})", tuple(row.values()))
        con.commit()
    finally:
        con.close()
