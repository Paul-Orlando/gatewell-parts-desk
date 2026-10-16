"""
Analytics tab: inventory levels, prices, sales, shipping costs, and currency effects.

Every query is limited to the employee's data scope (their warehouse, region, or the whole
company). Cost-based fields (stock value, carrier cost, margins) are removed afterwards by
auth.redact() for roles that can't see costs.
"""
from datetime import date, timedelta

from . import dates, db
from .auth import Employee, scope_sql
from .services import _choice, category_groups, warehouse_code

CATEGORY_NOTE = "Shipping and exchange figures cover whole orders, so they aren't split by category."

PERIODS = {"30": 30, "90": 90, "365": 365, "all": None}

# Every data section dashboard() returns, with a one-line description for the assistant's tool definition.
# tests/test_inputs.py checks this matches dashboard(), so a new section can't be left out.
SECTIONS = {
    "kpis": "Headline totals: units on hand, available, in transit, missing (units and value at cost), SKUs to reorder, "
            "stock value, orders, revenue, shipping cost, FX gain or loss",
    "inventory_by_warehouse": "Per warehouse (point in time): units on hand, in transit, missing units and missing "
                              "value at cost, SKUs to reorder, stock value. Use this to compare warehouses",
    "inventory_by_group": "Per category (point in time): units on hand, available, stock value",
    "missing_by_group": "Missing stock per category (point in time): units and value at cost. Rows are rounded; for the overall "
                        "total use units_missing and missing_value_usd in kpis (always included), never the sum of rows",
    "missing_by_warehouse_group": "Missing stock per warehouse and category (point in time; units and value at cost), largest first. "
                                  "Use this for questions like 'which warehouse has the most missing stock, and in which "
                                  "categories'. For overall totals use kpis (always included)",
    "low_stock": "Top 15 parts at or below reorder point (point in time), with days of cover and a short suggested action",
    "stock_aging": "Stock by days since last activity, point in time (0-30, 31-90, 91-180, 180+)",
    "sales_by_month": "Every month: domestic and international revenue, orders, carrier cost, shipping charged",
    "sales_by_quarter": "Every quarter of every year (e.g. 2025-Q2, 2026-Q2): orders and revenue, already totalled",
    "revenue_by_region": "Orders and revenue by customer region (selected period)",
    "revenue_by_country": "International orders, revenue, billed amount and FX gain or loss by country (selected period)",
    "sales_by_group": "Units sold and revenue by category (selected period)",
    "top_parts": "Top 10 parts by revenue (selected period)",
    "price_by_group": "Average list price by category and tier (OEM, Premium, Value)",
    "shipping_by_carrier": "Orders, average carrier cost and average charged per carrier (selected period)",
    "shipping_by_service": "Orders and average cost and charge per shipping service (selected period)",
}


POINT_IN_TIME = ("inventory_by_warehouse", "inventory_by_group", "missing_by_group", "missing_by_warehouse_group",
                 "low_stock", "stock_aging")
WHOLE_HISTORY = ("sales_by_month", "sales_by_quarter")


def section_notes(stock_as_of: str, period_covers: str) -> dict:
    """What each section's figures cover, so stock counts are never described with the sales period."""
    notes = {s: f"Point-in-time count as of {stock_as_of}. Not tied to the sales period; never describe it as "
                "'last N days'." for s in POINT_IN_TIME}
    notes.update({s: "Whole history, by " + ("month." if s == "sales_by_month" else "quarter.") for s in WHOLE_HISTORY})
    notes["price_by_group"] = f"Current list prices as of {stock_as_of}."
    notes["kpis"] = (f"Stock figures (units on hand, available, in transit, missing, backordered, SKUs, stock value, "
                     f"missing value) are as of {stock_as_of}. Orders, revenue, units sold, shipping and FX cover "
                     f"{period_covers}.")
    for s in SECTIONS:
        notes.setdefault(s, f"Covers {period_covers}.")
    return notes


def _scope(emp: Employee, warehouse: str | None, column: str):
    sc, sa = scope_sql(emp, column)
    if warehouse:
        allowed = emp.warehouses()
        if allowed is not None and warehouse.upper() not in allowed:
            warehouse = None                      # can't widen beyond scope; fall back to their scope
        else:
            sc += f" AND {column} = ?"
            sa = sa + [warehouse.upper()]
    return sc, sa


def _orders(category: str | None):
    """Where sales queries read orders from. With a category, each order carries only that category's lines
    (an order's total is the sum of its lines, so the figures stay comparable); without one, the orders table as is.
    Returns (FROM clause, its args, revenue column, billed-in-local-currency column)."""
    if not category:
        return "orders o", [], "order_total_usd", "total_due_local"
    return ("""(SELECT o.*, SUM(ol.line_total_usd) cat_revenue_usd, SUM(ol.line_total_local) cat_billed_local
               FROM orders o JOIN order_lines ol USING (order_id) JOIN parts p USING (part_id)
               WHERE p.category_group = ? GROUP BY o.order_id) o""", [category], "cat_revenue_usd", "cat_billed_local")


def dashboard(emp: Employee, period: str = "90", warehouse: str | None = None, category: str | None = None) -> dict:
    """Analytics for the employee's scope, optionally one warehouse within it and one category group. The category
    narrows every stock and sales figure; shipping and FX are per order, so they're left out (with a note)."""
    days = PERIODS.get(period, 90)
    category = _choice(category, category_groups(), "category")
    warehouse = warehouse_code(warehouse)         # a code or city; unknown values are an error, not an empty dashboard
    allowed = emp.warehouses()
    note = None
    if warehouse and allowed is not None and warehouse not in allowed:
        note = f"{warehouse} is outside your view ({emp.scope_label()}), so this shows your own scope."
        warehouse = None
    end = db.as_of()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ") if days else "0000"
    si, sia = _scope(emp, warehouse, "s.warehouse_code")
    so, soa = _scope(emp, warehouse, "o.fulfillment_warehouse")
    if category:                                  # added after the scope, so it can only narrow it
        si, sia = si + " AND s.category_group = ?", sia + [category]
    src, srca, rev, billed = _orders(category)
    pc, pca = (" AND p.category_group = ?", [category]) if category else ("", [])
    whole_order = "NULL" if category else ""      # shipping and FX columns when a category is selected

    inv = db.one(f"""SELECT SUM(s.qty_on_hand) units_on_hand, SUM(s.qty_available) units_available,
                            SUM(s.qty_in_transit) units_in_transit, SUM(s.qty_missing) units_missing,
                            SUM(s.qty_backordered) units_backordered, SUM(s.needs_reorder) skus_needing_reorder,
                            SUM(CASE WHEN s.qty_available = 0 AND s.avg_daily_demand > 0 THEN 1 ELSE 0 END) skus_out_of_stock,
                            COUNT(DISTINCT s.part_id) skus_stocked, ROUND(SUM(s.stock_value_usd)) stock_value_usd,
                            ROUND(SUM(s.qty_missing * i.unit_cost_usd)) missing_value_usd
                     FROM v_stock_position s JOIN inventory i USING (part_id, warehouse_code) WHERE 1=1 {si}""", *sia)
    sales = db.one(f"""SELECT COUNT(*) orders, ROUND(SUM({rev})) revenue_usd,
                              ROUND(AVG({rev}), 2) avg_order_value_usd,
                              ROUND(100.0 * SUM(CASE WHEN order_type = 'International' THEN {rev} END) / SUM({rev}), 1) international_revenue_pct,
                              {whole_order or 'ROUND(SUM(carrier_cost_usd))'} carrier_cost_usd, {whole_order or 'ROUND(SUM(shipping_usd))'} shipping_usd,
                              {whole_order or f'ROUND(100.0 * SUM(carrier_cost_usd) / SUM({rev}), 1)'} shipping_cost_pct_of_revenue,
                              {whole_order or 'ROUND(SUM(fx_gain_loss_usd), 2)'} fx_gain_loss_usd
                       FROM {src} WHERE o.status <> 'Cancelled' AND o.ordered_at_utc >= ? {so}""", *srca, start, *soa)
    units_sold = db.scalar(f"""SELECT SUM(ol.quantity) FROM order_lines ol JOIN orders o USING (order_id) JOIN parts p USING (part_id)
                               WHERE ol.line_status IN ('Shipped','Delivered','Returned') AND o.ordered_at_utc >= ? {so}{pc}""",
                           start, *soa, *pca)
    kpis = {**(inv or {}), **(sales or {}), "units_sold": units_sold or 0}

    stock_as_of = dates.as_of_central(end)
    if days:
        first = (end - timedelta(days=days)).date()
        period_covers = f"{first:%b} {first.day} – {end:%b} {end.day}, {end.year} (last {days} days)"
    else:
        first = db.scalar("SELECT MIN(ordered_at_utc) FROM orders")[:7]
        period_covers = f"all history ({date.fromisoformat(first + '-01'):%b %Y} – {end:%b %Y})"

    low_stock = db.rows(f"""SELECT s.part_number, s.part_name, s.fits_summary, s.warehouse_code, s.qty_available, s.reorder_point,
                                   s.qty_in_transit, s.qty_backordered, s.avg_daily_demand,
                                   ROUND(s.qty_available / NULLIF(s.avg_daily_demand, 0), 1) days_of_cover
                            FROM v_stock_position s WHERE s.needs_reorder = 1 {si}
                            ORDER BY s.qty_backordered DESC, days_of_cover ASC, s.avg_daily_demand DESC LIMIT 15""", *sia)
    from .recommend import recommend_for_part         # each row gets a short suggested action (read-only)
    for r in low_stock:
        r["suggestion"] = recommend_for_part(emp, r["part_number"], r["warehouse_code"])["suggestion"]

    return dict(
        period=period, warehouse=warehouse or "All in your view", category=category or "All categories",
        note=CATEGORY_NOTE if category else None, scope=emp.scope_label(), scope_note=note,
        as_of=end.strftime("%Y-%m-%d %H:%M UTC"), as_of_display=stock_as_of, stock_as_of=stock_as_of, period_covers=period_covers,
        section_notes=section_notes(stock_as_of, period_covers),
        kpis=kpis,
        inventory_by_group=db.rows(f"""SELECT s.category_group label, SUM(s.qty_on_hand) units, SUM(s.qty_available) available,
                                              ROUND(SUM(s.stock_value_usd)) stock_value_usd
                                       FROM v_stock_position s WHERE 1=1 {si} GROUP BY 1 ORDER BY units DESC""", *sia),
        inventory_by_warehouse=db.rows(f"""SELECT s.warehouse_code label, SUM(s.qty_on_hand) units, SUM(s.qty_in_transit) in_transit,
                                                  SUM(s.qty_missing) missing, ROUND(SUM(s.qty_missing * i.unit_cost_usd)) missing_value_usd,
                                                  SUM(s.needs_reorder) needs_reorder, ROUND(SUM(s.stock_value_usd)) stock_value_usd
                                           FROM v_stock_position s JOIN inventory i USING (part_id, warehouse_code)
                                           WHERE 1=1 {si} GROUP BY 1 ORDER BY units DESC""", *sia),
        stock_aging=db.rows(f"""SELECT CASE WHEN days_since_last_activity <= 30 THEN '0-30 days'
                                            WHEN days_since_last_activity <= 90 THEN '31-90 days'
                                            WHEN days_since_last_activity <= 180 THEN '91-180 days' ELSE '180+ days' END label,
                                       SUM(qty_on_hand) units, ROUND(SUM(stock_value_usd)) stock_value_usd
                                FROM v_stock_position s WHERE qty_on_hand > 0 {si} GROUP BY 1
                                ORDER BY MIN(days_since_last_activity)""", *sia),
        low_stock=low_stock,
        missing_by_group=db.rows(f"""SELECT s.category_group label, SUM(s.qty_missing) units,
                                            ROUND(SUM(s.qty_missing * i.unit_cost_usd)) missing_value_usd
                                     FROM v_stock_position s JOIN inventory i USING (part_id, warehouse_code)
                                     WHERE s.qty_missing > 0 {si} GROUP BY 1 ORDER BY units DESC""", *sia),
        missing_by_warehouse_group=db.rows(f"""SELECT s.warehouse_code, s.category_group label, SUM(s.qty_missing) units,
                                                      ROUND(SUM(s.qty_missing * i.unit_cost_usd)) missing_value_usd
                                               FROM v_stock_position s JOIN inventory i USING (part_id, warehouse_code)
                                               WHERE s.qty_missing > 0 {si} GROUP BY 1, 2
                                               ORDER BY SUM(SUM(s.qty_missing)) OVER (PARTITION BY s.warehouse_code) DESC,
                                                        s.warehouse_code, units DESC""", *sia),
        sales_by_month=db.rows(f"""SELECT substr(o.ordered_at_utc, 1, 7) label,
                                          ROUND(SUM(CASE WHEN order_type = 'Domestic' THEN {rev} ELSE 0 END)) domestic_revenue_usd,
                                          ROUND(SUM(CASE WHEN order_type = 'International' THEN {rev} ELSE 0 END)) international_revenue_usd,
                                          COUNT(*) orders, {whole_order or 'ROUND(SUM(carrier_cost_usd))'} carrier_cost_usd,
                                          {whole_order or 'ROUND(SUM(shipping_usd))'} shipping_usd
                                   FROM {src} WHERE o.status <> 'Cancelled' {so} GROUP BY 1 ORDER BY 1""", *srca, *soa),
        # whole-history quarters, already added up, so "sales in Q2" can be answered for every year without arithmetic
        sales_by_quarter=db.rows(f"""SELECT substr(o.ordered_at_utc, 1, 4) || '-Q' || ((CAST(substr(o.ordered_at_utc, 6, 2) AS INTEGER) + 2) / 3) label,
                                            COUNT(*) orders, ROUND(SUM({rev})) revenue_usd,
                                            MIN(substr(o.ordered_at_utc, 1, 10)) first_order_date, MAX(substr(o.ordered_at_utc, 1, 10)) last_order_date
                                     FROM {src} WHERE o.status <> 'Cancelled' {so} GROUP BY 1 ORDER BY 1""", *srca, *soa),
        revenue_by_region=db.rows(f"""SELECT o.ship_to_region label, COUNT(*) orders, ROUND(SUM({rev})) revenue_usd
                                      FROM {src} WHERE o.status <> 'Cancelled' AND o.ordered_at_utc >= ? {so}
                                      GROUP BY 1 ORDER BY revenue_usd DESC""", *srca, start, *soa),
        revenue_by_country=db.rows(f"""SELECT o.ship_to_country label, o.billing_currency currency, COUNT(*) orders,
                                              ROUND(SUM({rev})) revenue_usd, ROUND(SUM({billed})) billed_local,
                                              {whole_order or 'ROUND(SUM(fx_gain_loss_usd), 2)'} fx_gain_loss_usd
                                       FROM {src} WHERE o.status <> 'Cancelled' AND o.order_type = 'International'
                                       AND o.ordered_at_utc >= ? {so} GROUP BY 1, 2 ORDER BY revenue_usd DESC""", *srca, start, *soa),
        sales_by_group=db.rows(f"""SELECT p.category_group label, SUM(ol.quantity) units, ROUND(SUM(ol.line_total_usd)) revenue_usd
                                   FROM order_lines ol JOIN orders o USING (order_id) JOIN parts p USING (part_id)
                                   WHERE ol.line_status IN ('Shipped','Delivered','Returned') AND o.ordered_at_utc >= ? {so}{pc}
                                   GROUP BY 1 ORDER BY revenue_usd DESC""", start, *soa, *pca),
        top_parts=db.rows(f"""SELECT p.part_number, p.part_name, p.brand, p.fits_summary, SUM(ol.quantity) units,
                                     ROUND(SUM(ol.line_total_usd)) revenue_usd
                              FROM order_lines ol JOIN orders o USING (order_id) JOIN parts p USING (part_id)
                              WHERE ol.line_status IN ('Shipped','Delivered','Returned') AND o.ordered_at_utc >= ? {so}{pc}
                              GROUP BY p.part_id ORDER BY revenue_usd DESC LIMIT 10""", start, *soa, *pca),
        price_by_group=db.rows(f"""SELECT category_group label,
                                         ROUND(AVG(CASE WHEN quality_tier = 'OEM' THEN list_price_usd END), 2) oem_avg_price_usd,
                                         ROUND(AVG(CASE WHEN quality_tier = 'Premium' THEN list_price_usd END), 2) premium_avg_price_usd,
                                         ROUND(AVG(CASE WHEN quality_tier = 'Value' THEN list_price_usd END), 2) value_avg_price_usd,
                                         ROUND(AVG(unit_cost_usd / list_price_usd) * 100, 1) avg_cost_pct_of_list
                                  FROM parts p WHERE status = 'Active' {pc} GROUP BY 1 ORDER BY oem_avg_price_usd DESC""", *pca),
        shipping_by_carrier=[] if category else db.rows(f"""SELECT o.carrier label, COUNT(*) orders, ROUND(AVG(carrier_cost_usd), 2) avg_carrier_cost_usd,
                                               ROUND(AVG(shipping_usd), 2) avg_charged_usd, ROUND(SUM(carrier_cost_usd)) carrier_cost_usd,
                                               ROUND(100.0 * SUM(carrier_cost_usd) / SUM(order_total_usd), 1) cost_pct_of_revenue
                                        FROM orders o WHERE o.status <> 'Cancelled' AND o.ordered_at_utc >= ? {so}
                                        GROUP BY 1 ORDER BY orders DESC""", start, *soa),
        shipping_by_service=[] if category else db.rows(f"""SELECT o.carrier_service label, o.order_type, COUNT(*) orders,
                                               ROUND(AVG(carrier_cost_usd), 2) avg_carrier_cost_usd, ROUND(AVG(shipping_usd), 2) avg_charged_usd
                                        FROM orders o WHERE o.status <> 'Cancelled' AND o.ordered_at_utc >= ? {so}
                                        GROUP BY 1, 2 ORDER BY orders DESC LIMIT 15""", start, *soa),
        warehouses=[w["warehouse_code"] for w in db.rows("SELECT warehouse_code FROM warehouses ORDER BY warehouse_code")
                    if emp.warehouses() is None or w["warehouse_code"] in emp.warehouses()],
    )
