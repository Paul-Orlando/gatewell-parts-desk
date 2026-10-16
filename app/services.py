"""
Business queries shared by the screens and the AI assistant.

Every function takes the signed-in Employee, applies their data scope, and returns plain
dicts. Callers pass results through auth.redact() before anything leaves the server, so the
screens and the assistant can never show an employee more than their role allows.
"""
import re
from datetime import date, datetime

from . import db
from .auth import Employee, scope_sql

STOCK_COLS = """part_id, part_number, part_name, brand, brand_type, quality_tier, category, category_group,
                condition, size_class, weight_lb, hazmat, fits_summary, part_status"""


def _words(q: str) -> list[str]:
    return [_singular(w) for w in (q or "").replace(",", " ").split() if w]


def _singular(w: str) -> str:
    """Search words match as substrings, so 'plugs' must become 'plug' to find 'Spark Plug Set'
    ('batteries' -> 'battery', 'rotors' -> 'rotor'). A part number keeps matching: 'TY-59862' is in 'TY-59862S'."""
    if len(w) > 4 and w.lower().endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.lower().endswith("s") and not w.lower().endswith("ss"):
        return w[:-1]
    return w


# --------------------------------------------------------------------------- input checks
class BadInput(ValueError):
    """A filter value the data doesn't have. The message lists the valid choices, so a person or the
    assistant can correct it instead of getting an empty result that looks like 'nothing found'."""


# Names people use for a warehouse that aren't its code, city or name (LAX is in Ontario, CA; EWR is Newark's airport).
WAREHOUSE_ALIASES = {"LOS ANGELES": "LAX", "LA": "LAX", "EWR": "NWK", "NEW JERSEY": "NWK", "DALLAS FORT WORTH": "DFW"}


def _short_name(w: dict) -> str:
    return w["warehouse_name"].replace(" Distribution Center", "").replace(" Depot", "")


def warehouse_code(value: str | None) -> str | None:
    """Accept a warehouse code, city or name ('NWK', 'Newark', 'Newark Distribution Center', 'Seattle')."""
    if not value or not value.strip():
        return None
    v = " ".join(value.replace("-", " ").replace(",", " ").split()).upper()
    whs = db.rows("SELECT warehouse_code, warehouse_name, city, state FROM warehouses ORDER BY warehouse_code")
    for w in whs:
        if v in (w["warehouse_code"], w["city"].upper(), w["warehouse_name"].upper(), _short_name(w).upper()):
            return w["warehouse_code"]
    if v in WAREHOUSE_ALIASES:
        return WAREHOUSE_ALIASES[v]
    raise BadInput(f"Unknown warehouse '{value}'. Use one of: " + ", ".join(
        f"{w['warehouse_code']} ({_short_name(w)}" + (f", {w['city']}" if w["city"] != _short_name(w) else "") + f", {w['state']})"
        for w in whs) + ".")


def _choice(value: str | None, valid: list[str], what: str) -> str | None:
    """Match a value to one of the valid choices, ignoring case and a trailing 's'."""
    if value is None or not str(value).strip():
        return None
    v = str(value).strip().lower()
    for c in valid:
        if c.lower() in (v, v + "s", v.rstrip("s")):
            return c
    raise BadInput(f"Unknown {what} '{value}'. Use one of: {', '.join(valid)}.")


def order_statuses() -> list[str]:
    return [r["status"] for r in db.rows("SELECT DISTINCT status FROM orders ORDER BY status")]


def category_groups() -> list[str]:
    return [r["g"] for r in db.rows("SELECT DISTINCT category_group g FROM parts ORDER BY 1")]


def categories() -> list[str]:
    return [r["c"] for r in db.rows("""SELECT category_group c FROM parts UNION SELECT category FROM parts ORDER BY 1""")]


STOCK_FILTERS = ["low", "out", "missing", "aged"]
TRANSIT_STATUSES = ["In Transit", "Delayed", "Customs Hold"]


# --------------------------------------------------------------------------- vehicles
def vehicle_options(make: str | None = None, model: str | None = None) -> dict:
    out = {"makes": [r["make"] for r in db.rows("SELECT DISTINCT make FROM vehicles ORDER BY make")]}
    if make:
        out["models"] = [r["model"] for r in db.rows("SELECT DISTINCT model FROM vehicles WHERE make=? ORDER BY model", make)]
    if make and model:
        out["years"] = [r["year"] for r in db.rows("SELECT DISTINCT year FROM vehicles WHERE make=? AND model=? ORDER BY year DESC",
                                                   make, model)]
        out["engines"] = db.rows("SELECT DISTINCT engine_code, engine FROM vehicles WHERE make=? AND model=?", make, model)
    return out


# --------------------------------------------------------------------------- inventory
YEAR_IN_TEXT = re.compile(r"\b(?:19[5-9]\d|20[0-4]\d)\b")


def _engine_words(text: str) -> frozenset:
    """'3.5L V6 Twin-Turbo' -> {'3.5', 'v6', 'twin', 'turbo'}: case, a size's trailing L and hyphens don't matter."""
    words = re.sub(r"[-_,/]", " ", str(text or "").lower()).split()
    return frozenset(re.sub(r"^(\d+(?:\.\d+)?)l$", r"\1", w) for w in words if w)


def _match_engines(asked: str, candidates: list[str]) -> list[str]:
    """Engines that match what was asked: an exact word match wins ('2.0L I4' isn't '2.0L I4 Turbo'); otherwise every
    engine that has all the asked words ('3.5L Twin-Turbo' -> '3.5L V6 Twin-Turbo'; '3.5' may match several)."""
    want = _engine_words(asked)
    if not want:
        return []
    exact = [e for e in candidates if _engine_words(e) == want]
    return exact or [e for e in candidates if want <= _engine_words(e)]


def _resolve_vehicle(make: str | None, model: str | None) -> tuple[str | None, str | None, str | None]:
    """Our make and model names for what was typed (any case). A model name given as the make ('Torvik') is read as
    that make and model. Returns (make, model, note); an unknown make returns make None and a note listing ours."""
    makes = {r["make"].lower(): r["make"] for r in db.rows("SELECT DISTINCT make FROM vehicles")}
    models = {r["model"].lower(): (r["make"], r["model"]) for r in db.rows("SELECT DISTINCT make, model FROM vehicles")}
    note = None
    m = (make or "").strip()
    if m:
        if m.lower() in makes:
            make = makes[m.lower()]
        elif m.lower() in models and (not model or model.strip().lower() == m.lower()):
            make, model = models[m.lower()]
            note = f"Read '{m}' as the {make} {model}."
        else:
            return None, None, (f"No make '{m}' in our catalog. Our makes: {', '.join(sorted(makes.values()))}. "
                                "Ask which one they mean.")
    if model and model.strip().lower() in models:
        model = models[model.strip().lower()][1]
    return make, model, note


def search_inventory(emp: Employee, q: str | None = None, year: int | None = None, make: str | None = None,
                     model: str | None = None, category: str | None = None, warehouse: str | None = None,
                     stock_filter: str | None = None, limit: int = 50, engine: str | None = None) -> dict:
    """Parts matching a text search and/or vehicle, with stock totals (company-wide or one warehouse).
    stock_filter: low (at or below reorder point), out (none available), missing (count shortfalls), aged (no activity 180+ days).
    engine: part of the engine name ('3.5', 'Twin-Turbo', '5.0L V8'), used with a vehicle.
    'count' is the rows returned; 'total' and 'totals' cover every match, so a capped list is never mistaken for all of it.
    When a vehicle without an engine matches parts that fit different engines, 'engines' lists them, so the
    engine can be asked for before parts are offered."""
    warehouse = warehouse_code(warehouse)
    category = _choice(category, categories(), "category")
    stock_filter = _choice(stock_filter, STOCK_FILTERS, "stock filter")
    pre_notes = []
    if make or model:
        # a year typed into the make or model ('Torvik 2018', model '2018') is the year filter
        years = [y for s in (make, model) if s for y in YEAR_IN_TEXT.findall(str(s))]
        if years and not year:
            year = int(years[0])
        make = YEAR_IN_TEXT.sub("", make or "").strip() or None
        model = YEAR_IN_TEXT.sub("", model or "").strip() or None
    if make or model:
        make, model, vnote = _resolve_vehicle(make, model)
        if vnote and make is None:                 # unknown make: say so, list ours
            return {"count": 0, "total": 0, "totals": {}, "warehouse": warehouse or "All warehouses", "results": [],
                    "note": vnote}
        if vnote:
            pre_notes.append(vnote)
    where, args = ["p.status = 'Active'"], []
    for w in _words(q):
        where.append("(s.part_number LIKE ? OR s.part_name LIKE ? OR s.brand LIKE ? OR s.fits_summary LIKE ? OR s.category LIKE ?)")
        args += [f"%{w}%"] * 5
    sub, sargs = [], []
    if year or make or model:
        if year: sub.append("v.year = ?"); sargs.append(int(year))
        if make: sub.append("v.make = ?"); sargs.append(make)
        if model: sub.append("v.model = ?"); sargs.append(model)
        engine_note, matched = None, None
        if engine and engine.strip():
            cands = [r["engine"] for r in db.rows(
                f"SELECT DISTINCT v.engine FROM vehicles v WHERE {' AND '.join(sub) or '1=1'} ORDER BY v.engine", *sargs)]
            matched = _match_engines(engine, cands)
            if len(matched) == 1:
                sub.append("v.engine = ?"); sargs.append(matched[0])
            elif matched:
                sub.append(f"v.engine IN ({','.join('?' * len(matched))})"); sargs += matched
                engine_note = (f"'{engine.strip()}' matches several engines ({', '.join(matched)}). "
                               "Ask which one before listing parts.")
            else:
                engine_note = (f"No engine matches '{engine.strip()}' for this vehicle. It has: {', '.join(cands) or 'none'}. "
                               "Ask which one.")
                matched = cands
        where.append(f"s.part_id IN (SELECT f.part_id FROM part_fitment f JOIN vehicles v USING (vehicle_id) WHERE {' AND '.join(sub)})")
        args += sargs
    if category:
        where.append("(s.category = ? OR s.category_group = ?)"); args += [category, category]
    if warehouse:
        where.append("s.warehouse_code = ?"); args.append(warehouse.upper())
    having = ""
    if stock_filter == "low":
        having = "HAVING SUM(s.needs_reorder) > 0"
    elif stock_filter == "out":
        having = "HAVING SUM(s.qty_available) = 0 AND SUM(s.avg_daily_demand) > 0"
    elif stock_filter == "missing":
        having = "HAVING SUM(s.qty_missing) > 0"
    elif stock_filter == "aged":
        having = "HAVING MIN(s.days_since_last_activity) >= 180 AND SUM(s.qty_on_hand) > 0"
    grouped = f"""
        SELECT s.part_id, s.part_number, s.part_name, s.brand, s.brand_type, s.quality_tier, s.category, s.fits_summary,
               s.size_class, s.weight_lb, s.hazmat, p.list_price_usd, p.unit_cost_usd,
               SUM(s.qty_on_hand) qty_on_hand, SUM(s.qty_available) qty_available, SUM(s.qty_reserved) qty_reserved,
               SUM(s.qty_in_transit) qty_in_transit, SUM(s.qty_backordered) qty_backordered,
               SUM(s.qty_missing) qty_missing, SUM(s.qty_damaged) qty_damaged, SUM(s.needs_reorder) warehouses_needing_reorder,
               COUNT(*) warehouses_stocking, ROUND(SUM(s.stock_value_usd), 2) stock_value_usd,
               MIN(s.days_since_last_activity) days_since_last_activity
        FROM v_stock_position s JOIN parts p USING (part_id)
        WHERE {' AND '.join(where)}
        GROUP BY s.part_id {having}"""
    order = {"missing": "qty_missing DESC, qty_available DESC", "low": "qty_available ASC, warehouses_needing_reorder DESC",
             "aged": "days_since_last_activity DESC"}.get(stock_filter, "qty_available DESC")
    results = db.rows(f"SELECT * FROM ({grouped}) ORDER BY {order}, part_number LIMIT ?", *args, int(limit))
    t = db.one(f"""SELECT COUNT(*) parts, SUM(qty_on_hand) qty_on_hand, SUM(qty_available) qty_available,
                          SUM(qty_in_transit) qty_in_transit, SUM(qty_missing) qty_missing, ROUND(SUM(stock_value_usd), 2) stock_value_usd
                   FROM ({grouped})""", *args)
    out = {"count": len(results), "total": t.pop("parts"), "totals": t, "warehouse": warehouse or "All warehouses",
           "results": results}
    notes = list(pre_notes)
    if out["total"] > len(results):
        out["partial"] = True
        notes.append(f"Showing {len(results)} of {out['total']} matching parts. This list is cut short: narrow by category, "
                     "engine or year (or a part number) before listing parts, and never present these rows as complete. "
                     "'totals' covers all matches; don't add up or extrapolate the rows shown.")
    if sub and engine and engine.strip() and engine_note:
        out["engines"] = matched
        notes.append(engine_note)
    if sub and not (engine and engine.strip()):
        fit = db.rows(f"""SELECT DISTINCT f.part_id, v.engine FROM part_fitment f JOIN vehicles v USING (vehicle_id)
                          WHERE {' AND '.join(sub)} AND f.part_id IN (SELECT part_id FROM ({grouped}))""", *sargs, *args)
        engines = sorted({r["engine"] for r in fit})
        per_part = {}
        for r in fit:
            per_part.setdefault(r["part_id"], set()).add(r["engine"])
        if len(engines) > 1 and any(len(e) < len(engines) for e in per_part.values()):
            out["engines"] = engines
            notes.append(f"These parts fit different engines ({', '.join(engines)}). Ask which engine before listing "
                         "parts, unless the question already says.")
    if notes:
        out["note"] = " ".join(notes)
    return out


def part_detail(emp: Employee, part_number: str) -> dict | None:
    p = db.one("SELECT * FROM parts WHERE part_number = ?", part_number.strip().upper())
    if not p:
        return None
    replacement = None
    if p["status"] == "Superseded" and p["superseded_by_part_id"]:
        replacement = db.one("SELECT part_number, part_name FROM parts WHERE part_id = ?", p["superseded_by_part_id"])
    stock = db.rows("""SELECT warehouse_code, warehouse_city, warehouse_state, region, timezone, bin_location, qty_on_hand,
                              qty_reserved, qty_damaged, qty_missing, qty_available, qty_in_transit, qty_backordered,
                              reorder_point, reorder_qty, avg_daily_demand, needs_reorder, stock_value_usd,
                              last_received_utc, last_sold_utc, last_counted_utc, days_since_last_activity
                       FROM v_stock_position WHERE part_id = ? ORDER BY warehouse_code""", p["part_id"])
    transit = db.rows("""SELECT shipment_id, shipment_type, origin_name, origin_country, destination_warehouse, mode, carrier,
                                status, eta_destination_local, exception_note, quantity
                         FROM v_in_transit WHERE part_id = ? ORDER BY eta_utc""", p["part_id"])
    fits = db.rows("""SELECT v.make, v.model, MIN(v.year) year_from, MAX(v.year) year_to, GROUP_CONCAT(DISTINCT v.engine) engines
                      FROM part_fitment f JOIN vehicles v USING (vehicle_id) WHERE f.part_id = ?
                      GROUP BY v.make, v.model ORDER BY v.make, v.model""", p["part_id"])
    equivalents = db.rows("""SELECT p2.part_number, p2.brand, p2.quality_tier, p2.list_price_usd,
                                    (SELECT SUM(qty_available) FROM v_stock_position WHERE part_id = p2.part_id) qty_available
                             FROM part_interchange i
                             JOIN parts p2 ON p2.part_id = CASE WHEN i.part_id = ? THEN i.interchanges_with_part_id ELSE i.part_id END
                             WHERE (i.part_id = ? OR i.interchanges_with_part_id = ?) AND p2.status = 'Active'""",
                          p["part_id"], p["part_id"], p["part_id"])
    sc, sa = scope_sql(emp, "fulfillment_warehouse")
    sales = _last_12_months(db.rows(f"""SELECT order_month, SUM(quantity) units, ROUND(SUM(line_total_usd), 2) revenue_usd
                                        FROM v_sales WHERE part_id = ? {sc} GROUP BY order_month""", p["part_id"], *sa))
    supplier = db.one("SELECT supplier_name, city, country FROM suppliers WHERE supplier_id = ?", p["primary_supplier_id"])
    return dict(part=p, replacement=replacement, supplier=supplier, stock_by_warehouse=stock, in_transit=transit,
                fits=fits, equivalents=equivalents, monthly_sales=sales,
                totals=dict(on_hand=sum(s["qty_on_hand"] for s in stock), available=sum(s["qty_available"] for s in stock),
                            in_transit=sum(s["qty_in_transit"] for s in stock), missing=sum(s["qty_missing"] for s in stock),
                            backordered=sum(s["qty_backordered"] for s in stock)))


def _last_12_months(rows: list[dict]) -> list[dict]:
    """The 12 calendar months ending at the data's 'as of' month, oldest first, with months without sales as zero."""
    end = db.as_of()
    months = [f"{y:04d}-{m:02d}" for y, m in
              ((end.year + (end.month - 1 - i) // 12, (end.month - 1 - i) % 12 + 1) for i in range(11, -1, -1))]
    by_month = {r["order_month"]: r for r in rows}
    return [by_month.get(m, {"order_month": m, "units": 0, "revenue_usd": 0.0}) for m in months]


def in_transit(emp: Employee, warehouse: str | None = None, part_number: str | None = None,
               status: str | None = None, origin_country: str | None = None, limit: int = 50) -> dict:
    warehouse = warehouse_code(warehouse)
    status = _choice(status, TRANSIT_STATUSES, "shipment status")
    where, args = ["1=1"], []
    if warehouse: where.append("destination_warehouse = ?"); args.append(warehouse)
    if part_number: where.append("part_number = ?"); args.append(part_number.strip().upper())
    if status: where.append("status = ?"); args.append(status)
    if origin_country: where.append("origin_country LIKE ?"); args.append(f"%{origin_country}%")
    grouped = f"""SELECT shipment_id, shipment_type, po_number, transfer_number, origin_name, origin_city, origin_country, origin_timezone,
                         destination_warehouse, mode, carrier, port_of_entry, ship_date_origin_local,
                         eta_destination_local, status, exception_note, currency,
                         COUNT(*) lines, SUM(quantity) units, MIN(eta_utc) eta_sort
                  FROM v_in_transit WHERE {' AND '.join(where)} GROUP BY shipment_id"""
    shipments = db.rows(f"{grouped} ORDER BY eta_sort LIMIT ?", *args, int(limit))
    now = db.as_of()
    for s in shipments:
        late = (now - datetime.fromisoformat(s.pop("eta_sort").replace("Z", "+00:00"))).days
        if late >= 1:                              # say so in words, so an answer doesn't leave it out
            eta = datetime.fromisoformat(s["eta_destination_local"])
            s["note"] = f"{late} day{'s' if late != 1 else ''} past its ETA ({eta.strftime('%b')} {eta.day})"
    t = db.one(f"SELECT COUNT(*) shipments, SUM(units) units FROM ({grouped})", *args)
    return {"count": len(shipments), "total": t["shipments"], "total_units": t["units"] or 0, "shipments": shipments}


# --------------------------------------------------------------------------- orders
ORDER_LIST_COLS = """o.order_id, o.ordered_at_utc, o.ordered_at_local, o.order_type, o.customer_id, c.customer_name,
                     o.customer_type, o.channel, o.ship_to_city, o.ship_to_state, o.ship_to_country, o.fulfillment_warehouse,
                     o.status, o.carrier, o.carrier_service, o.tracking_number, o.billing_currency, o.total_due_local,
                     o.order_total_usd, o.payment_status, o.customs_status"""


def country_codes() -> list[str]:
    return [r["country_code"] for r in db.rows("SELECT country_code FROM countries ORDER BY country_code")]


def _order_date(value: str | None, name: str) -> str | None:
    """A YYYY-MM-DD order date, or None. Anything else is a clear error."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10]).isoformat()
    except ValueError:
        raise BadInput(f"{name} must be a date like 2026-10-05 (YYYY-MM-DD), not '{value}'.")


def search_orders(emp: Employee, q: str | None = None, status: str | None = None, order_type: str | None = None,
                  warehouse: str | None = None, customer_type: str | None = None, days: int | None = None,
                  limit: int = 50, ship_to_country: str | None = None, date_from: str | None = None,
                  date_to: str | None = None) -> dict:
    """date_from / date_to: order date in the customer's local time, inclusive. Filters only narrow the
    employee's scope; 'total' and 'totals' cover every match."""
    warehouse = warehouse_code(warehouse)
    if ship_to_country:
        ship_to_country = str(ship_to_country).strip().upper()
        if ship_to_country not in country_codes():
            raise BadInput(f"Unknown country code '{ship_to_country}'. Use one of: {', '.join(country_codes())}.")
    date_from, date_to = _order_date(date_from, "date_from"), _order_date(date_to, "date_to")
    if date_from and date_to and date_from > date_to:
        raise BadInput(f"date_from ({date_from}) is after date_to ({date_to}).")
    status = _choice(status, order_statuses(), "order status")
    order_type = _choice(order_type, ["Domestic", "International"], "order type")
    customer_type = _choice(customer_type, ["Dealership", "Individual"], "customer type")
    where, args = ["1=1"], []
    sc, sa = scope_sql(emp, "o.fulfillment_warehouse")
    if q:
        qq = q.strip()
        where.append("""(o.order_id = ? OR o.customer_id = ? OR o.tracking_number = ? OR c.customer_name LIKE ?
                         OR o.order_id IN (SELECT ol.order_id FROM order_lines ol JOIN parts p USING (part_id) WHERE p.part_number = ?))""")
        args += [qq.upper(), qq.upper(), qq, f"%{qq}%", qq.upper()]
    if status: where.append("o.status = ?"); args.append(status)
    if order_type: where.append("o.order_type = ?"); args.append(order_type)
    if warehouse: where.append("o.fulfillment_warehouse = ?"); args.append(warehouse)
    if customer_type: where.append("o.customer_type = ?"); args.append(customer_type)
    if ship_to_country: where.append("o.ship_to_country_code = ?"); args.append(ship_to_country)
    if date_from: where.append("substr(o.ordered_at_local, 1, 10) >= ?"); args.append(date_from)
    if date_to: where.append("substr(o.ordered_at_local, 1, 10) <= ?"); args.append(date_to)
    if days:
        where.append("o.ordered_at_utc >= strftime('%Y-%m-%dT%H:%M:%SZ', ?, ?)"); args += [db.as_of().strftime("%Y-%m-%dT%H:%M:%SZ"), f"-{int(days)} days"]
    base = f"FROM orders o JOIN customers c USING (customer_id) WHERE {' AND '.join(where)} {sc}"
    res = db.rows(f"SELECT {ORDER_LIST_COLS} {base} ORDER BY o.ordered_at_utc DESC LIMIT ?", *args, *sa, int(limit))
    total = db.scalar(f"SELECT COUNT(*) {base}", *args, *sa)
    out = {"count": len(res), "total": total, "results": res}
    # Totals across many orders are an analytics capability: only roles with Analytics get them. Over every match,
    # not just the rows shown; cancelled orders are left out of the total and counted separately (USD only: local
    # totals are in mixed currencies).
    if emp.perms["analytics"]:
        out["totals"] = db.one(f"""SELECT SUM(o.status <> 'Cancelled') orders,
                                          ROUND(SUM(CASE WHEN o.status <> 'Cancelled' THEN o.order_total_usd END), 2) order_total_usd,
                                          SUM(o.status = 'Cancelled') cancelled_orders {base}""", *args, *sa)
    if total > len(res):
        out["partial"] = True
        out["note"] = (f"Showing the latest {len(res)} of {total} matching orders. These rows are a sample: don't add up, "
                       "average or extrapolate them to describe all matches.")
    return out


def order_detail(emp: Employee, order_id: str) -> dict | None:
    sc, sa = scope_sql(emp, "o.fulfillment_warehouse")
    o = db.one(f"SELECT o.*, c.customer_name FROM orders o JOIN customers c USING (customer_id) WHERE o.order_id = ? {sc}",
               order_id.strip().upper(), *sa)
    if not o:
        return None
    lines = db.rows("""SELECT ol.line_no, p.part_number, p.part_name, p.brand, ol.quantity, ol.line_status, ol.currency,
                              ol.unit_price_local, ol.line_total_local, ol.unit_price_usd, ol.line_total_usd,
                              ol.core_charge_usd, ol.core_status, ol.country_of_origin, ol.hs_code, ol.usmca_eligible,
                              v.year || ' ' || v.make || ' ' || v.model AS for_vehicle, i.bin_location
                       FROM order_lines ol JOIN parts p USING (part_id) JOIN vehicles v USING (vehicle_id)
                       LEFT JOIN inventory i ON i.part_id = ol.part_id AND i.warehouse_code = ol.fulfillment_warehouse
                       WHERE ol.order_id = ? ORDER BY ol.line_no""", o["order_id"])
    customer = db.one("""SELECT customer_id, customer_type, customer_name, city, state, country, region, timezone,
                                franchise_make, price_tier, payment_terms, billing_currency
                         FROM customers WHERE customer_id = ?""", o["customer_id"])
    cases = db.rows("""SELECT case_id, opened_at_utc, channel, department_id, contact_reason, status, assigned_to
                       FROM support_cases WHERE order_id = ? ORDER BY opened_at_utc""", o["order_id"])
    return dict(order=o, lines=lines, customer=customer, support_cases=cases)


# --------------------------------------------------------------------------- support cases
def list_cases(emp: Employee, status: str | None = None, department: str | None = None, q: str | None = None,
               limit: int = 100) -> dict:
    department = _choice(department, [r["department_id"] for r in db.rows("SELECT department_id FROM support_departments")],
                         "team (department)")
    status = _choice(status, ["active"] + [r["status"] for r in db.rows("SELECT DISTINCT status FROM support_cases ORDER BY 1")],
                     "case status")                # 'active' = everything not resolved
    where, args = ["1=1"], []
    if status == "active": where.append("sc.status <> 'Resolved'")
    elif status: where.append("sc.status = ?"); args.append(status)
    if department: where.append("sc.department_id = ?"); args.append(department)
    if q:
        where.append("(sc.case_id = ? OR sc.order_id = ? OR sc.customer_id = ? OR c.customer_name LIKE ?)")
        args += [q.upper(), q.upper(), q.upper(), f"%{q}%"]
    res = db.rows(f"""SELECT sc.*, c.customer_name, c.customer_type, d.department_name,
                             e.first_name || ' ' || e.last_name AS assigned_name
                      FROM support_cases sc JOIN customers c USING (customer_id)
                      JOIN support_departments d ON d.department_id = sc.department_id
                      LEFT JOIN employees e ON e.employee_id = sc.assigned_to
                      WHERE {' AND '.join(where)} ORDER BY sc.opened_at_utc DESC LIMIT ?""", *args, int(limit))
    counts = db.rows("SELECT status, COUNT(*) n FROM support_cases GROUP BY status")
    return {"count": len(res), "status_counts": counts, "results": res}


# --------------------------------------------------------------------------- support teams (read-only directory)
def _clock(hhmm: str) -> str:
    """'07:00' -> '7:00 AM'."""
    h, m = int(hhmm[:2]), hhmm[3:5]
    return f"{(h - 1) % 12 + 1}:{m} {'AM' if h < 12 else 'PM'}"


def _span(spec: str) -> str:
    return "closed" if spec == "Closed" else " - ".join(_clock(x) for x in spec.split("-"))


def support_teams(emp: Employee, now: datetime | None = None) -> dict:
    """Every support team with what it handles, how to reach it, its hours in Central time, and whether it's
    open at the app's as-of time (or 'now', for tests). Read-only; the same facts the assistant's contact_team
    tool gives every role."""
    from . import agent_tools as AT, dates
    now = now or db.as_of()
    co = db.one("SELECT toll_free_phone, international_phone, main_email FROM company")
    central = lambda dt: dt.astimezone(AT.HQ_TZ)
    when = lambda dt: f"{dates.day(central(dt).date())}, {central(dt).strftime('%I:%M %p').lstrip('0')} Central"
    teams = []
    for d in db.rows("SELECT * FROM support_departments ORDER BY department_name"):
        open_now = AT._is_open(d, now)
        if open_now:
            loc = central(now)
            close = loc.replace(hour=AT._hours(d, loc)[1], minute=0, second=0, microsecond=0)
            status = f"Open now, until {when(close)}"
        else:
            status = f"Closed, opens {when(AT._next_open(d, now))}"
        teams.append(dict(department_id=d["department_id"], department_name=d["department_name"], handles=d["handles"],
                          phone=d["phone"], email=d["email"], languages=d["languages"], open_now=open_now,
                          status=status, hours=f"Mon-Fri {_span(d['weekday_hours'])}, Sat {_span(d['saturday_hours'])}, "
                                               f"Sun {_span(d['sunday_hours'])} (Central)"))
    return dict(as_of_display=dates.as_of_central(now), main_phone=co["toll_free_phone"],
                international_phone=co["international_phone"], main_email=co["main_email"], teams=teams)
