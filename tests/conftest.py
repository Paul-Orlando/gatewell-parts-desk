"""Test setup: run against a throwaway copy of the database so tests never change the real data."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_tmp = Path(tempfile.mkdtemp(prefix="gatewell-test-"))
shutil.copy(ROOT / "data" / "car_parts_inventory.db", _tmp / "test.db")
os.environ["GATEWELL_DB"] = str(_tmp / "test.db")
os.environ["GATEWELL_LOG_DIR"] = str(_tmp / "logs")
os.environ.pop("OPENROUTER_API_KEY", None)
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.server import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def _emp(title, warehouse=None, region=None):
    sql = "SELECT employee_id FROM employees WHERE role = ?"
    args = [title]
    if warehouse:
        sql += " AND warehouse_code = ?"; args.append(warehouse)
    if region:
        sql += " AND region = ?"; args.append(region)
    return db.scalar(sql + " ORDER BY employee_id LIMIT 1", *args)


@pytest.fixture(scope="session")
def ids():
    """One sample employee per role, looked up by title so tests survive data regeneration."""
    return {
        "warehouse": _emp("Warehouse Associate", "ATL"),
        "cs": _emp("Customer Service Rep"),
        "cs_sup": _emp("Customer Service Supervisor"),
        "wh_manager": _emp("Warehouse Manager", "ATL"),
        "regional": _emp("Regional Manager", region="Northeast"),
        "director": _emp("Operations Director"),
    }


@pytest.fixture(scope="session")
def tmp_dir():
    return _tmp


def headers(emp_id):
    return {"X-Employee-Id": emp_id}
