"""
Suggested actions for low, out-of-stock and backordered parts: transfers from other warehouses, a reorder from
the supplier, and substitute parts. Read-only: nothing is ordered, moved or saved. People decide.

An employee gets suggestions only *for* warehouses in their data scope, but any warehouse can be a transfer
source (stock levels are visible to every role). Shipping estimates are cost data (estimated_cost_usd), removed
by auth.redact() for roles that can't see costs; the summary sentence only mentions cost for roles that can.
Warehouse roles get transfers and substitutes, not reorders (purchasing isn't their call).
"""
from datetime import date

from . import agent_tools as AT
from . import db
from .auth import Employee
from .services import BadInput, warehouse_code

AT.DB_PATH = db.DB_PATH
AT.NOW = db.as_of()

LABEL = "Suggestion only. Nothing is ordered or moved."
FAR_SUPPLIERS = {"Japan", "South Korea", "China", "Germany"}       # ocean freight: about 30 days; else about 8


def _lead_days(country: str) -> int:
    return 30 if country in FAR_SUPPLIERS else 8


def _stock(part_id: str) -> dict:
    return {r["warehouse_code"]: r for r in db.rows(
        """SELECT warehouse_code, warehouse_city, warehouse_state, qty_available, qty_in_transit, qty_backordered,
                  reorder_point, reorder_qty, avg_daily_demand
           FROM v_stock_position WHERE part_id = ?""", part_id)}


def _target(emp: Employee, warehouse: str | None, stock: dict) -> str:
    """The warehouse the suggestions are for: the one asked for (must be in scope), the employee's own, or the
    warehouse in their scope that needs the part most."""
    wh = warehouse_code(warehouse) or (emp.warehouse_code if emp.scope == "Warehouse" else None)
    allowed = emp.warehouses()
    if wh and allowed is not None and wh not in allowed:
        raise BadInput(f"{wh} is outside your view ({emp.scope_label()}). You can get suggestions for: "
                       f"{', '.join(allowed)}.")
    if wh:
        return wh
    mine = [s for c, s in stock.items() if allowed is None or c in allowed]
    if not mine:
        raise BadInput("This part isn't stocked at any warehouse in your view.")
    worst = max(mine, key=lambda s: (s["qty_backordered"], s["reorder_point"] - s["qty_available"]))
    return worst["warehouse_code"]


def _ground(part_number: str, qty: int, src: str, state: str) -> dict | None:
    """Cheapest ground service from one warehouse to another (business address), from the rate engine."""
    q = AT.quote_shipping([{"part_number": part_number, "quantity": max(qty, 1)}], "US", state, residential=False,
                          from_warehouse=src)
    grounds = [o for o in q.get("options", []) if o["speed"] == "Ground"] if q.get("ok") else []
    if not grounds:
        return None
    g = grounds[0]
    svc = g["service"] if g["service"].startswith(g["carrier"]) else f'{g["carrier"]} {g["service"]}'
    return dict(service=svc, transit_days=g["transit_business_days"],
                estimated_cost_usd=g["cost_usd"])


def _substitutes(part_id: str, wh: str) -> list[dict]:
    """Equivalent parts with stock available at the warehouse, most available first."""
    ids = [r["pid"] for r in db.rows("""SELECT CASE WHEN part_id = ? THEN interchanges_with_part_id ELSE part_id END pid
                                         FROM part_interchange WHERE part_id = ? OR interchanges_with_part_id = ?""",
                                      part_id, part_id, part_id)]
    if not ids:
        return []
    return db.rows(f"""SELECT s.part_number, s.brand, s.quality_tier, p.list_price_usd, s.qty_available
                       FROM v_stock_position s JOIN parts p USING (part_id)
                       WHERE s.part_id IN ({','.join('?' * len(ids))}) AND s.warehouse_code = ? AND p.status = 'Active'
                         AND s.qty_available > 0 ORDER BY s.qty_available DESC""", *ids, wh)


def _max_days(days: str) -> int:
    return int(str(days).split("-")[-1])


def recommend_for_part(emp: Employee, part_number: str, warehouse: str | None = None) -> dict:
    """Transfer options, a reorder recommendation and substitutes for one part at one warehouse."""
    p = db.one("SELECT part_id, part_number, part_name, primary_supplier_id FROM parts WHERE part_number = ?",
               (part_number or "").strip().upper())
    if not p:
        raise BadInput(f"No part with number '{part_number}'.")
    stock = _stock(p["part_id"])
    wh = _target(emp, warehouse, stock)
    out = dict(part_number=p["part_number"], part_name=p["part_name"], for_warehouse=wh, label=LABEL)
    t = stock.get(wh)
    if not t:
        out.update(need_now=0, transfer_options=[], substitutes=[],
                   summary=f"{p['part_number']} isn't stocked at {wh}.", suggestion="Not stocked here")
        return out
    avail, transit, back, rp = t["qty_available"], t["qty_in_transit"], t["qty_backordered"], t["reorder_point"]
    need_now = max(rp + back - avail, 0)
    out.update(qty_available=avail, qty_in_transit=transit, qty_backordered=back, reorder_point=rp, need_now=need_now)

    # transfers: only stock above the source's own reorder point
    transfers = []
    if need_now:
        for code, s in stock.items():
            spare = s["qty_available"] - s["reorder_point"]
            if code == wh or spare <= 0:
                continue
            opt = dict(warehouse_code=code, warehouse_city=s["warehouse_city"], spare_qty=spare,
                       suggested_qty=min(spare, need_now))
            opt.update(_ground(p["part_number"], opt["suggested_qty"], code, t["warehouse_state"]) or {})
            transfers.append(opt)
        transfers.sort(key=lambda o: (_max_days(o.get("transit_days", 99)), o.get("estimated_cost_usd") or 0,
                                      -o["suggested_qty"]))
    out["transfer_options"] = transfers

    # reorder: what's already inbound first
    nxt = db.one("""SELECT eta_destination_local, quantity, mode, status FROM v_in_transit
                    WHERE part_id = ? AND destination_warehouse = ? ORDER BY eta_utc LIMIT 1""", p["part_id"], wh)
    covered = transit > 0 and avail + transit - back > rp
    reorder = None
    if emp.role != "warehouse" and (need_now or transit):
        sup = db.one("SELECT supplier_name, country FROM suppliers WHERE supplier_id = ?", p["primary_supplier_id"]) or {}
        qty = 0 if covered else max(t["reorder_qty"] - transit, rp + 1 + back - avail - transit, 0)
        reorder = dict(covered_by_inbound=covered, suggested_qty=qty, supplier_name=sup.get("supplier_name"),
                       country=sup.get("country"), lead_time_days=_lead_days(sup.get("country", "")))
        if nxt:
            reorder.update(next_eta_local=nxt["eta_destination_local"], quantity=nxt["quantity"], mode=nxt["mode"],
                           status=nxt["status"])
        if not need_now and not qty:
            reorder = None
    if reorder:
        out["reorder"] = reorder

    out["substitutes"] = _substitutes(p["part_id"], wh) if need_now else []
    out["summary"], out["suggestion"] = _words(emp, out, t, nxt, covered)
    return out


def _day(iso: str) -> str:
    """"2026-10-14..." -> "Wed, Oct 14", the date style used across the app."""
    d = date.fromisoformat(iso[:10])
    return f"{d:%a}, {d:%b} {d.day}"


def _words(emp: Employee, r: dict, t: dict, nxt: dict | None, covered: bool) -> tuple[str, str]:
    """A plain-English summary sentence and a short suggestion for tables."""
    wh, avail, back, rp = r["for_warehouse"], r["qty_available"], r["qty_backordered"], r["reorder_point"]
    if not r["need_now"]:
        return (f"{wh} has {avail} available, above its reorder point of {rp}. No action needed.", "No action needed")
    parts = [f"{wh} is out" if not avail else f"{wh} has {avail} available (reorder point {rp})"]
    if back:
        parts[0] += f", {back} backordered"
    parts[0] += "."
    if nxt:
        eta = _day(nxt["eta_destination_local"])
        parts.append(f"{nxt['quantity']} arrive{'s' if nxt['quantity'] == 1 else ''} {eta} by {nxt['mode'].lower()}" +
                     (f" ({nxt['status'].lower()})" if nxt["status"] != "In Transit" else "") + ".")
    short = []
    tr = r["transfer_options"]
    if tr:
        b = tr[0]
        how = ""
        if "transit_days" in b:
            how = f" ({b['transit_days']} business days" + (f", about ${b['estimated_cost_usd']:,.2f}" if emp.perms["cost"] else "") + ")"
        parts.append(f"Fastest cover: transfer {b['suggested_qty']} from {b['warehouse_code']}{how}.")
        short.append(f"Transfer {b['suggested_qty']} from {b['warehouse_code']}")
    ro = r.get("reorder")
    if covered:
        parts.append("Inbound stock covers the shortfall, so no reorder is needed.")
        short.append(f"covered by inbound {t['qty_in_transit']}")
    elif ro and ro["suggested_qty"]:
        parts.append(f"Reorder {ro['suggested_qty']} from {ro['supplier_name']} ({ro['country']}, about "
                     f"{ro['lead_time_days']} days).")
        short.append(f"reorder {ro['suggested_qty']}")
    if r["substitutes"]:
        s = r["substitutes"][0]
        parts.append(f"Or offer {s['part_number']} ({s['quality_tier']}, {s['qty_available']} available).")
        if not short:
            short.append(f"Offer {s['part_number']}")
    if not short:
        short.append("No stock to transfer")
    text = "; ".join(short)
    return " ".join(parts), text[0].upper() + text[1:]


def low_stock_rows(emp: Employee, warehouse: str | None = None, category: str | None = None, limit: int = 15) -> list[dict]:
    """Parts at or below their reorder point, or backordered, in the employee's scope: backorders first."""
    from .auth import scope_sql
    sc, sa = scope_sql(emp, "s.warehouse_code")
    where, args = "", []
    if warehouse:
        where += " AND s.warehouse_code = ?"; args.append(warehouse)
    if category:
        where += " AND s.category_group = ?"; args.append(category)
    return db.rows(f"""SELECT s.part_number, s.part_name, s.fits_summary, s.warehouse_code, s.qty_available,
                              s.reorder_point, s.qty_in_transit, s.qty_backordered, s.avg_daily_demand,
                              ROUND(s.qty_available / NULLIF(s.avg_daily_demand, 0), 1) days_of_cover
                       FROM v_stock_position s WHERE (s.needs_reorder = 1 OR s.qty_backordered > 0) {sc}{where}
                       ORDER BY s.qty_backordered DESC, days_of_cover ASC, s.avg_daily_demand DESC LIMIT ?""",
                   *sa, *args, int(limit))


def recommend_for_warehouse(emp: Employee, warehouse: str | None = None, category: str | None = None,
                            limit: int = 15) -> dict:
    """The top low-stock and backordered parts in scope (or one warehouse in it), each with a short suggestion."""
    from .services import _choice, category_groups
    wh = warehouse_code(warehouse)
    allowed = emp.warehouses()
    if wh and allowed is not None and wh not in allowed:
        raise BadInput(f"{wh} is outside your view ({emp.scope_label()}). You can get suggestions for: "
                       f"{', '.join(allowed)}.")
    category = _choice(category, category_groups(), "category")
    rows = low_stock_rows(emp, wh, category, min(int(limit), 25))
    for r in rows:
        rec = recommend_for_part(emp, r["part_number"], r["warehouse_code"])
        r["suggestion"] = rec["suggestion"]
        r["summary"] = rec["summary"]
    return dict(warehouse=wh or "All warehouses in your view", category=category or "All categories", label=LABEL,
                count=len(rows), recommendations=rows)
