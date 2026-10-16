"""Guard: no real make, carrier or engine trade name comes back into the data or the app.

The map lives in data_generator/name_map.py; docs/NAME_MAP.md is the maintainers' reference
and is the one place old names may appear, so it is not scanned.
"""
import importlib.util
import re
import sqlite3
from pathlib import Path

from app import db

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("name_map", ROOT / "data_generator" / "name_map.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

DENY = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in sorted(M.DENYLIST, key=len, reverse=True)) + r")(?![\w-])")


def _con():
    return sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True)


def _distinct(sql):
    with _con() as con:
        return {r[0] for r in con.execute(sql) if r[0] is not None}


def test_vehicle_names_come_from_the_fictional_set():
    for table in ("vehicles", "platforms"):
        assert _distinct(f"SELECT make FROM {table}") <= M.FICTIONAL_MAKES
        assert _distinct(f"SELECT model FROM {table}") <= M.FICTIONAL_MODELS
    assert _distinct("SELECT franchise_make FROM customers") <= M.FICTIONAL_MAKES


def test_brands_and_engines_come_from_the_fictional_set():
    assert _distinct("SELECT brand FROM parts WHERE brand_type = 'OEM'") <= M.FICTIONAL_OEM_BRANDS
    assert _distinct("SELECT oem_family FROM parts") <= set(M.FAMILY.values())
    families = {code.split("-")[0] for code in _distinct("SELECT engine_code FROM vehicles")}
    assert families <= set(M.FAMILY.values())
    engines = _distinct("SELECT engine FROM vehicles")
    assert set(M.ENGINE_NAME.values()) <= engines and not engines & set(M.ENGINE_NAME)


def test_carriers_and_services_come_from_the_fictional_set():
    own = {"Gatewell Delivery", "Freight forwarder"}
    assert _distinct("SELECT carrier FROM shipping_services") <= M.FICTIONAL_CARRIERS | own
    assert _distinct("SELECT carrier FROM shipping_surcharges") <= M.FICTIONAL_CARRIERS
    assert _distinct("SELECT carrier FROM orders") <= M.FICTIONAL_CARRIERS | own
    parcel = _distinct("SELECT service_code FROM shipping_services WHERE carrier NOT IN ('Gatewell Delivery', 'Freight forwarder')")
    assert parcel == {code for code, _ in M.SERVICE.values()}
    names = _distinct("SELECT service_name FROM shipping_services WHERE service_code IN (%s)"
                      % ",".join(f"'{c}'" for c in parcel))
    assert names == {name for _, name in M.SERVICE.values()}


def test_no_real_names_in_database_text():
    hits = []
    with _con() as con:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for t in tables:
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")') if r[2] == "TEXT"]
            for c in cols:
                for (v,) in con.execute(f'SELECT DISTINCT "{c}" FROM "{t}" WHERE "{c}" IS NOT NULL'):
                    if isinstance(v, str) and DENY.search(v):
                        hits.append(f"{t}.{c}: {v[:80]}")
    assert not hits, hits[:20]


def test_no_real_names_in_app_code():
    app = ROOT / "app"
    files = [p for p in app.rglob("*") if p.suffix in (".py", ".js", ".html", ".css")
             and "vendor" not in p.parts and "__pycache__" not in p.parts]
    assert files
    hits = [f"{p.relative_to(ROOT)}:{i}: {line.strip()[:100]}"
            for p in files for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if DENY.search(line)]
    assert not hits, hits
