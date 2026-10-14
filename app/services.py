"""
Business queries shared by the screens and the AI assistant.

Every function takes the signed-in Employee, applies their data scope, and returns plain
dicts. Callers pass results through auth.redact() before anything leaves the server, so the
screens and the assistant can never show an employee more than their role allows.
"""
from . import db
from .auth import Employee, scope_sql

STOCK_COLS = """part_id, part_number, part_name, brand, brand_type, quality_tier, category, category_group,
                condition, size_class, weight_lb, hazmat, fits_summary, part_status"""


def _words(q: str) -> list[str]:
    return [w for w in (q or "").replace(",", " ").split() if w]


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
def search_inventory(emp: Employee, q: str | None = None, year: int | None = None, make: str | None = None,
                     model: str | None = None, category: str | None = None, warehouse: str | None = None,
                     stock_filter: str | None = None, limit: int = 50) -> dict:
    """Parts matching a text search and/or vehicle, with stock totals (company-wide or one warehouse).
    stock_filter: low (at or below reorder point), out (none available), missing (count shortfalls), aged (no activity 180+ days)."""
    where, args = ["p.status = 'Active'"], []
    for w in _words(q):
        where.append("(s.part_number LIKE ? OR s.part_name LIKE ? OR s.brand LIKE ? OR s.fits_summary LIKE ? OR s.category LIKE ?)")
        args += [f"%{w}%"] * 5
    if year or make or model:
        sub, sargs = [], []
        if year: sub.append("v.year = ?"); sargs.append(int(year))
        if make: sub.append("v.make = ?"); sargs.append(make)
        if model: sub.append("v.model = ?"); sargs.append(model)
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
    sql = f"""
        SELECT s.part_id, s.part_number, s.part_name, s.brand, s.brand_type, s.quality_tier, s.category, s.fits_summary,
               s.size_class, s.weight_lb, s.hazmat, p.list_price_usd, p.unit_cost_usd,
               SUM(s.qty_on_hand) qty_on_hand, SUM(s.qty_available) qty_available, SUM(s.qty_reserved) qty_reserved,
               SUM(s.qty_in_transit) qty_in_transit, SUM(s.qty_backordered) qty_backordered,
               SUM(s.qty_missing) qty_missing, SUM(s.qty_damaged) qty_damaged, SUM(s.needs_reorder) warehouses_needing_reorder,
               COUNT(*) warehouses_stocking, ROUND(SUM(s.stock_value_usd), 2) stock_value_usd,
               MIN(s.days_since_last_activity) days_since_last_activity
        FROM v_stock_position s JOIN parts p USING (part_id)
        WHERE {' AND '.join(where)}
        GROUP BY s.part_id {having}
        ORDER BY qty_available DESC, s.part_number LIMIT ?"""
    results = db.rows(sql, *args, int(limit))
    return {"count": len(results), "warehouse": warehouse or "All warehouses", "results": results}


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
    sales = db.rows(f"""SELECT order_month, SUM(quantity) units, ROUND(SUM(line_total_usd), 2) revenue_usd
                        FROM v_sales WHERE part_id = ? {sc} GROUP BY order_month ORDER BY order_month DESC LIMIT 12""",
                    p["part_id"], *sa)
    supplier = db.one("SELECT supplier_name, city, country FROM suppliers WHERE supplier_id = ?", p["primary_supplier_id"])
    return dict(part=p, replacement=replacement, supplier=supplier, stock_by_warehouse=stock, in_transit=transit,
                fits=fits, equivalents=equivalents, monthly_sales=sales,
                totals=dict(on_hand=sum(s["qty_on_hand"] for s in stock), available=sum(s["qty_available"] for s in stock),
                            in_transit=sum(s["qty_in_transit"] for s in stock), missing=sum(s["qty_missing"] for s in stock),
                            backordered=sum(s["qty_backordered"] for s in stock)))


def in_transit(emp: Employee, warehouse: str | None = None, part_number: str | None = None,
               status: str | None = None, origin_country: str | None = None, limit: int = 50) -> dict:
    where, args = ["1=1"], []
    if warehouse: where.append("destination_warehouse = ?"); args.append(warehouse.upper())
    if part_number: where.append("part_number = ?"); args.append(part_number.upper())
    if status: where.append("status = ?"); args.append(status)
    if origin_country: where.append("origin_country LIKE ?"); args.append(f"%{origin_country}%")
    shipments = db.rows(f"""SELECT shipment_id, shipment_type, po_number, transfer_number, origin_name, origin_city, origin_country,
                                   destination_warehouse, mode, carrier, port_of_entry, ship_date_origin_local,
                                   eta_destination_local, status, exception_note, currency,
                                   COUNT(*) lines, SUM(quantity) units
                            FROM v_in_transit WHERE {' AND '.join(where)}
                            GROUP BY shipment_id ORDER BY eta_utc LIMIT ?""", *args, int(limit))
    return {"count": len(shipments), "shipments": shipments}


# --------------------------------------------------------------------------- orders
ORDER_LIST_COLS = """o.order_id, o.ordered_at_utc, o.ordered_at_local, o.order_type, o.customer_id, c.customer_name,
                     o.customer_type, o.channel, o.ship_to_city, o.ship_to_state, o.ship_to_country, o.fulfillment_warehouse,
                     o.status, o.carrier, o.carrier_service, o.tracking_number, o.billing_currency, o.total_due_local,
                     o.order_total_usd, o.payment_status, o.customs_status"""


def search_orders(emp: Employee, q: str | None = None, status: str | None = None, order_type: str | None = None,
                  warehouse: str | None = None, customer_type: str | None = None, days: int | None = None,
                  limit: int = 50) -> dict:
    where, args = ["1=1"], []
    sc, sa = scope_sql(emp, "o.fulfillment_warehouse")
    if q:
        qq = q.strip()
        where.append("""(o.order_id = ? OR o.customer_id = ? OR o.tracking_number = ? OR c.customer_name LIKE ?
                         OR o.order_id IN (SELECT ol.order_id FROM order_lines ol JOIN parts p USING (part_id) WHERE p.part_number = ?))""")
        args += [qq.upper(), qq.upper(), qq, f"%{qq}%", qq.upper()]
    if status: where.append("o.status = ?"); args.append(status)
    if order_type: where.append("o.order_type = ?"); args.append(order_type)
    if warehouse: where.append("o.fulfillment_warehouse = ?"); args.append(warehouse.upper())
    if customer_type: where.append("o.customer_type = ?"); args.append(customer_type)
    if days:
        where.append("o.ordered_at_utc >= strftime('%Y-%m-%dT%H:%M:%SZ', ?, ?)"); args += [db.as_of().strftime("%Y-%m-%dT%H:%M:%SZ"), f"-{int(days)} days"]
    res = db.rows(f"""SELECT {ORDER_LIST_COLS} FROM orders o JOIN customers c USING (customer_id)
                      WHERE {' AND '.join(where)} {sc} ORDER BY o.ordered_at_utc DESC LIMIT ?""", *args, *sa, int(limit))
    return {"count": len(res), "results": res}


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
