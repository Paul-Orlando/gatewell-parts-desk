#!/usr/bin/env python3
"""
Gatewell Auto Parts - agent tools (prototype)

Functions the chat agent calls to answer questions. Every function returns a plain dict
(JSON-ready), so each one can be offered to a language model as a tool. The app's assistant
(app/assistant.py) defines its own role-based tool list; TOOL_SCHEMAS and run_tool() below are
a standalone reference.

    python3 agent_tools.py demo      # run example quotes, FAQ lookups and handoffs

All shipping rates and surcharges come from the dataset's synthetic rate cards.
For live pricing, replace _service_cost() with calls to each carrier's rating API.
"""
import json, math, re, sqlite3, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DB_PATH = "car_parts_inventory.db"
NOW = datetime(2026, 10, 11, 21, 0, tzinfo=timezone.utc)   # dataset "as of"; use datetime.now(timezone.utc) with live data
CM_PER_IN, KG_PER_LB = 2.54, 0.45359237
HQ_TZ = ZoneInfo("America/Chicago")
FAQ_PAGE = "https://www.gatewellautoparts.example/faq"
REFUND_LIMIT_USD = 250.0          # the bot can't promise refunds or credits above this
NEGOTIATED_DISCOUNT = 0.45        # our (synthetic) contract discount off carrier transportation charges
CARTON_MAX_LB = 50.0              # several units of the same part share a carton up to this weight
MAX_FAILED_ATTEMPTS = 2           # after this many unanswered tries, offer a live person

def _con(db=None):
    c = sqlite3.connect(db or DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def _one(c, sql, *args):
    r = c.execute(sql, args).fetchone()
    return dict(r) if r else None

def _all(c, sql, *args):
    return [dict(r) for r in c.execute(sql, args).fetchall()]

def _fx(c, code):
    r = _one(c, "SELECT f.units_per_usd, f.rate_date, cu.decimals, cu.symbol FROM v_fx_latest f "
                "JOIN currencies cu USING (currency_code) WHERE f.currency_code = ?", code)
    if not r: raise ValueError(f"Unknown currency {code}")
    return r

def _money(v, dec):
    return round(v, dec)

def _resolve_part(c, part_number):
    p = _one(c, "SELECT * FROM parts WHERE part_number = ?", part_number.strip().upper())
    if not p: return None, f"No part found with number {part_number}."
    note = None
    if p["status"] == "Superseded" and p["superseded_by_part_id"]:
        newp = _one(c, "SELECT * FROM parts WHERE part_id = ?", p["superseded_by_part_id"])
        note = f"{p['part_number']} was replaced by {newp['part_number']} on {p['supersession_date']}; quoting the replacement."
        p = newp
    return p, note

def _customer(c, customer_id):
    return _one(c, "SELECT * FROM customers WHERE customer_id = ?", customer_id) if customer_id else None

# ============================================================================ part price
def get_part_price(part_number, customer_id=None, quantity=1, currency=None):
    """Price of a part for a given customer: list price, the customer's price, core charge,
    local-currency amounts at today's rate, and where it's in stock."""
    c = _con()
    p, note = _resolve_part(c, part_number)
    if not p: return {"found": False, "message": note}
    cu = _customer(c, customer_id)
    disc = cu["discount_pct"] if cu else 0.0
    ccy = (currency or (cu["billing_currency"] if cu else "USD")).upper()
    fx = _fx(c, ccy)
    margin = 0.02 if ccy != "USD" else 0.0
    unit_usd = round(p["list_price_usd"] * (1 - disc), 2)
    to_local = lambda usd: _money(usd * fx["units_per_usd"] * (1 + margin), fx["decimals"])
    stock = _all(c, "SELECT warehouse_code, warehouse_city, warehouse_state, qty_available, qty_in_transit "
                    "FROM v_stock_position WHERE part_id = ? AND (qty_available > 0 OR qty_in_transit > 0) "
                    "ORDER BY qty_available DESC", p["part_id"])
    alts = _all(c, "SELECT p2.part_number, p2.brand, p2.quality_tier, p2.list_price_usd FROM part_interchange i "
                   "JOIN parts p2 ON p2.part_id = CASE WHEN i.part_id = ? THEN i.interchanges_with_part_id ELSE i.part_id END "
                   "WHERE (i.part_id = ? OR i.interchanges_with_part_id = ?) AND p2.status = 'Active'",
               p["part_id"], p["part_id"], p["part_id"])
    out = {
        "found": True, "note": note, "part_number": p["part_number"], "part_name": p["part_name"], "brand": p["brand"],
        "quality_tier": p["quality_tier"], "condition": p["condition"], "fits": p["fits_summary"],
        "weight_lb": p["weight_lb"], "size_class": p["size_class"], "hazmat": bool(p["hazmat"]),
        "quantity": quantity, "list_price_usd": p["list_price_usd"],
        "customer_type": cu["customer_type"] if cu else "Individual (guest)",
        "discount_pct": disc, "unit_price_usd": unit_usd, "subtotal_usd": round(unit_usd * quantity, 2),
        "core_charge_usd": round(p["core_charge_usd"] * quantity, 2),
        "currency": ccy, "fx_rate_units_per_usd": fx["units_per_usd"], "fx_rate_date": fx["rate_date"],
        "fx_margin_pct": margin, "unit_price_local": to_local(unit_usd),
        "subtotal_local": _money(to_local(unit_usd) * quantity, fx["decimals"]),
        "core_charge_local": to_local(p["core_charge_usd"] * quantity),
        "in_stock_total": sum(s["qty_available"] for s in stock),
        "stock_by_warehouse": stock[:6],
        "equivalent_parts": alts,
    }
    c.close()
    return out

# ============================================================================ shipping
def _packages(parts_qty):
    """Turn order lines into shipping packages. Small parts share one box; every unit of a
    larger part ships in its own box (how parts distributors usually pack)."""
    pkgs, small_w, small_vol = [], 0.0, 0.0
    for p, q in parts_qty:
        dims_in = sorted([p["length_cm"] / CM_PER_IN, p["width_cm"] / CM_PER_IN, p["height_cm"] / CM_PER_IN], reverse=True)
        if p["size_class"] == "Small":
            small_w += p["weight_lb"] * q
            small_vol += dims_in[0] * dims_in[1] * dims_in[2] * q
        else:
            per_box = 1 if (p["shipping_class"] == "Oversize" or p["hazmat"]) else max(1, int(CARTON_MAX_LB // p["weight_lb"]))
            left = q
            while left > 0:
                n = min(per_box, left); left -= n
                d = sorted([dims_in[0], dims_in[1], dims_in[2] * n], reverse=True)
                pkgs.append(dict(contents=f"{p['part_number']} x{n}", weight_lb=round(p["weight_lb"] * n + 0.5, 2),
                                 dims_in=[round(x + 1, 1) for x in d], hazmat=bool(p["hazmat"])))
    if small_w:
        side = round((small_vol * 1.3) ** (1 / 3) + 1, 1)
        pkgs.append(dict(contents="small parts (combined box)", weight_lb=round(small_w + 0.5, 2),
                         dims_in=[side, side, side], hazmat=False))
    return pkgs

def _surcharges(c, carrier):
    return {r["surcharge_code"]: r for r in _all(c, "SELECT * FROM shipping_surcharges WHERE carrier = ?", carrier)}

def _add_business_days(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5: n -= 1
    return d

def _ship_date(wh_tz, now):
    loc = now.astimezone(ZoneInfo(wh_tz))
    d = loc.date()
    if loc.weekday() >= 5 or loc.hour >= 15:      # weekend or after the 3:00 PM cutoff -> next business day
        d = _add_business_days(d, 1)
    return d

def _service_cost(c, svc, rate, pkgs, residential, scope, sur=None):
    """Estimated carrier charge for one service (our negotiated rate). Returns (cost_usd, breakdown)
    or (None, reason). `sur` can be a preloaded {code: row} surcharge map instead of a DB lookup."""
    sur = sur if sur is not None else _surcharges(c, svc["carrier"])
    is_ground = svc["speed"] == "Ground"
    breakdown, total = [], 0.0
    for pk in pkgs:
        L, W, H = pk["dims_in"]
        lg = L + 2 * (W + H)
        if svc["max_weight_lb"] and pk["weight_lb"] > svc["max_weight_lb"]:
            return None, f"Package over {svc['max_weight_lb']} lb limit"
        if svc["max_length_plus_girth_in"] and lg > svc["max_length_plus_girth_in"]:
            return None, f"Package too large ({lg:.0f} in length + girth; limit {svc['max_length_plus_girth_in']})"
        if pk["hazmat"] and not svc["hazmat_lead_acid_allowed"]:
            return None, "Lead-acid batteries can only ship by Parcelora or Velocair ground"
        vol = L * W * H
        dimw = vol / svc["dim_divisor"] if (svc["carrier"] != "Postara" or vol > 1728) else 0
        billable = max(math.ceil(pk["weight_lb"]), math.ceil(dimw), 1)
        transport = (rate["first_lb_usd"] + rate["additional_lb_usd"] * (billable - 1)) * (1 - NEGOTIATED_DISCOUNT)
        extras = []
        if svc["carrier"] == "Postara":
            if L > 30: extras.append(("NONSTD_30", sur["NONSTD_30"]["amount_usd"]))
            elif L > 22: extras.append(("NONSTD_22", sur["NONSTD_22"]["amount_usd"]))
        else:
            large = (lg > 130 or L > 96) if svc["carrier"] != "Globexa Express" else (L > 47 and lg > 130)
            handling = L > 48 or W > 30 or pk["weight_lb"] > 50
            if large: extras.append(("LARGE_PKG", sur["LARGE_PKG"]["amount_usd"]))
            elif handling: extras.append(("ADD_HANDLING", sur["ADD_HANDLING"]["amount_usd"]))
            if pk["hazmat"] and "HAZMAT_GND" in sur: extras.append(("HAZMAT_GND", sur["HAZMAT_GND"]["amount_usd"]))
            if residential:
                code = "RESI_GND" if is_ground and "RESI_GND" in sur else "RESI_AIR"
                if code in sur: extras.append((code, sur[code]["amount_usd"]))
        subtotal = transport + sum(a for _, a in extras)
        if scope == "Domestic": fuel_code = "FUEL_GND" if is_ground else "FUEL_AIR"
        else: fuel_code = "FUEL_GND" if is_ground and "FUEL_GND" in sur else "FUEL_INTL"
        fuel_pct = sur[fuel_code]["percent"] if fuel_code in sur else 0.0
        fuel = subtotal * fuel_pct / 100
        total += subtotal + fuel
        breakdown.append(dict(package=pk["contents"], billable_weight_lb=billable, dimensions_in=pk["dims_in"],
                              transportation_usd=round(transport, 2),
                              surcharges={sur[k]["surcharge_name"]: a for k, a in extras},
                              fuel_surcharge_usd=round(fuel, 2), package_total_usd=round(subtotal + fuel, 2)))
    return round(total, 2), breakdown

def quote_shipping(items, ship_to_country="US", ship_to_state=None, residential=True, customer_id=None,
                   from_warehouse=None, now=None):
    """Shipping options from every major carrier for a list of {part_number, quantity},
    sorted by price, with estimated delivery dates and any services that can't carry the order."""
    now = now or NOW
    c = _con()
    cu = _customer(c, customer_id)
    if cu:
        ship_to_country, ship_to_state = cu["country_code"], cu["state"]
        residential = cu["customer_type"] == "Individual"
    ship_to_country = (ship_to_country or "US").upper()
    country = _one(c, "SELECT * FROM countries WHERE country_code = ?", ship_to_country)
    if not country:
        return {"ok": False, "message": f"We don't ship to {ship_to_country} yet. See {FAQ_PAGE} for countries we serve."}
    domestic = ship_to_country == "US"
    if domestic and not ship_to_state:
        return {"ok": False, "message": "Which U.S. state is this shipping to?"}
    parts_qty, notes = [], []
    for it in items:
        p, note = _resolve_part(c, it["part_number"])
        if not p: return {"ok": False, "message": note}
        if note: notes.append(note)
        parts_qty.append((p, int(it.get("quantity", 1))))
    has_haz = any(p["hazmat"] for p, _ in parts_qty)
    if has_haz and country["overseas"]:
        return {"ok": False, "message": "Lead-acid batteries can't be shipped overseas. We ship them within the U.S. "
                                        "and to Canada and Mexico only.", "faq": FAQ_PAGE + "#why-can-t-i-choose-air-shipping-for-a-battery"}
    # choose the warehouse: the serving one if it has everything, else the one with the most coverage
    if domestic:
        serving = [_one(c, "SELECT serving_warehouse FROM states WHERE state_code = ?", ship_to_state.upper())["serving_warehouse"]]
    else:
        serving = [w.strip() for w in country["serving_warehouses"].split(",")]
    def coverage(wh):
        return sum(min(q, (_one(c, "SELECT qty_available FROM v_stock_position WHERE part_id=? AND warehouse_code=?",
                                p["part_id"], wh) or {"qty_available": 0})["qty_available"]) for p, q in parts_qty)
    need = sum(q for _, q in parts_qty)
    wh = from_warehouse
    if not wh:
        cands = serving + [w["warehouse_code"] for w in _all(c, "SELECT warehouse_code FROM warehouses") if w["warehouse_code"] not in serving]
        scored = sorted(cands, key=lambda w_: (-coverage(w_), cands.index(w_)))
        wh = scored[0]
        if coverage(wh) < need: notes.append("Not every item is in stock at one warehouse; quoting from the warehouse with the most stock.")
        elif wh not in serving: notes.append(f"Ships from {wh} because the nearest warehouse is out of stock.")
    whrow = _one(c, "SELECT * FROM warehouses WHERE warehouse_code = ?", wh)
    zone = str(_one(c, "SELECT zone FROM shipping_zones_domestic WHERE warehouse_code=? AND state_code=?", wh,
                    ship_to_state.upper())["zone"]) if domestic else country["shipping_zone"]
    pkgs = _packages(parts_qty)
    ship_day = _ship_date(whrow["timezone"], now)
    goods_usd = sum(p["list_price_usd"] * q * (1 - (cu["discount_pct"] if cu else 0)) for p, q in parts_qty)
    ccy = cu["billing_currency"] if cu else (country["currency_code"] if not domestic else "USD")
    fx = _fx(c, ccy); margin = 0.02 if ccy != "USD" else 0.0
    services = _all(c, "SELECT * FROM shipping_services WHERE scope = ? AND offered_to_customers = 1",
                    "Domestic" if domestic else "International")
    options, unavailable = [], []
    for s in services:
        if s["service_code"] == "PCL_STD_CAMX" and ship_to_country not in ("CA", "MX"): continue
        if s["service_code"] == "VLC_IG" and ship_to_country != "CA": continue
        rate = _one(c, "SELECT * FROM shipping_rates WHERE service_code=? AND zone=?", s["service_code"], zone)
        if not rate: continue
        cost, detail = _service_cost(c, s, rate, pkgs, residential, s["scope"])
        if cost is None:
            unavailable.append({"carrier": s["carrier"], "service": s["service_name"], "reason": detail})
            continue
        eta = _add_business_days(ship_day, rate["transit_days_max"])
        options.append(dict(carrier=s["carrier"], service=s["service_name"], service_code=s["service_code"],
                            speed=s["speed"], cost_usd=cost,
                            cost_local=_money(cost * fx["units_per_usd"] * (1 + margin), fx["decimals"]),
                            transit_business_days=f'{rate["transit_days_min"]}-{rate["transit_days_max"]}'
                            if rate["transit_days_min"] != rate["transit_days_max"] else str(rate["transit_days_min"]),
                            ships_on=ship_day.isoformat(), estimated_delivery_by=eta.isoformat(), packages=detail))
    options.sort(key=lambda o: o["cost_usd"])
    free = None
    dealer = bool(cu and cu["customer_type"] == "Dealership")
    oversize = any(p["shipping_class"] == "Oversize" for p, _ in parts_qty)
    if domestic and not dealer and oversize and goods_usd >= 99.0:
        notes.append("Oversize parts aren't eligible for free shipping on individual orders.")
    if domestic and (dealer or (goods_usd >= 99.0 and not oversize)):
        grounds = [o for o in options if o["speed"] == "Ground"]
        if grounds:
            free = grounds[0]["service"]
            grounds[0]["customer_pays_usd"] = 0.0
            notes.append(f"Free ground shipping applies ({free}).")
    for o in options: o.setdefault("customer_pays_usd", o["cost_usd"])
    if not domestic:      # say what isn't included, in the same words as full_quote, so no tax rule gets guessed
        notes.append("Import tax is paid by the importer on arrival (DAP)." if dealer else
                     f'These amounts exclude import tax: {country["import_tax_name"]} {country["import_tax_pct"]}% '
                     "collected at checkout (DDP). A total with tax comes from a full customer quote.")
    c.close()
    return dict(ok=True, ship_from=f'{whrow["warehouse_name"]} ({whrow["city"]}, {whrow["state"]})', warehouse_code=wh,
                ship_to=(ship_to_state.upper() + ", US") if domestic else country["country_name"], zone=zone,
                residential=residential, currency=ccy, fx_rate_units_per_usd=fx["units_per_usd"],
                package_count=len(pkgs), total_weight_lb=round(sum(p["weight_lb"] for p in pkgs), 2),
                options=options, unavailable=unavailable, notes=notes,
                disclaimer="Estimated rates for prototyping; final carrier charges may differ.")

def full_quote(items, customer_id=None, ship_to_country="US", ship_to_state=None, residential=True):
    """Everything a customer pays: parts, core charges, shipping per carrier, and import tax for
    international individuals (collected at checkout, DDP), in the customer's currency."""
    c = _con()
    cu = _customer(c, customer_id)
    lines = [get_part_price(it["part_number"], customer_id, int(it.get("quantity", 1)),
                            currency=None if cu else (None if (ship_to_country or "US").upper() == "US" else
                                                      _one(c, "SELECT currency_code FROM countries WHERE country_code=?",
                                                           ship_to_country.upper())["currency_code"]))
             for it in items]
    bad = [l for l in lines if not l.get("found")]
    if bad: return {"ok": False, "message": bad[0]["message"]}
    ship = quote_shipping(items, ship_to_country, ship_to_state, residential, customer_id)
    if not ship.get("ok"): return ship
    country = _one(c, "SELECT * FROM countries WHERE country_code = ?", cu["country_code"] if cu else ship_to_country.upper())
    ccy = lines[0]["currency"]; dec = _fx(c, ccy)["decimals"]
    parts_local = _money(sum(l["subtotal_local"] for l in lines), dec)
    cores_local = _money(sum(l["core_charge_local"] for l in lines), dec)
    collect_tax = country["country_code"] != "US" and not (cu and cu["customer_type"] == "Dealership")
    totals = []
    for o in ship["options"]:
        ship_local = _money(o["customer_pays_usd"] * ship["fx_rate_units_per_usd"] * (1.02 if ccy != "USD" else 1), dec)
        tax = _money((parts_local + ship_local) * (country["import_tax_pct"] or 0) / 100, dec) if collect_tax else 0
        totals.append(dict(carrier=o["carrier"], service=o["service"], delivery_by=o["estimated_delivery_by"],
                           parts=parts_local, core_charges=cores_local, shipping=ship_local,
                           import_tax=tax, total=_money(parts_local + cores_local + ship_local + tax, dec)))
    c.close()
    return dict(ok=True, currency=ccy, lines=[{k: l[k] for k in ("part_number", "part_name", "brand", "quantity",
                "unit_price_local", "subtotal_local", "core_charge_local", "in_stock_total")} for l in lines],
                import_tax=(f'{country["import_tax_name"]} {country["import_tax_pct"]}% collected at checkout (DDP)'
                            if collect_tax else ("Paid by the importer on arrival (DAP)" if country["country_code"] != "US"
                                                 else "U.S. sales tax not included in this prototype")),
                ship_from=ship["ship_from"], options=totals, unavailable=ship["unavailable"], notes=ship["notes"],
                disclaimer=ship["disclaimer"])

# ============================================================================ FAQ
_STOP = set("a an the i my me we you your our is are do does can how what when where why which to of for in on it "
            "this that with and or be will if at by from doesn don didn isn still question answer about please".split())
def _stem(w):
    if w.endswith("ies") and len(w) > 4: return w[:-3] + "y"
    if w.endswith("ing") and len(w) > 5:
        w = w[:-3]
        return w[:-1] if len(w) > 2 and w[-1] == w[-2] else w
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3: return w[:-1]
    return w

def _tokens(t):
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in _STOP and len(w) > 1]

def search_faq(question, limit=3):
    """Best-matching FAQ answers with links to the FAQ page."""
    c = _con()
    q = set(_tokens(question))
    scored = []
    for f in _all(c, "SELECT * FROM faq"):
        kw, qs, an = set(_tokens(f["keywords"])), set(_tokens(f["question"])), set(_tokens(f["answer"]))
        score = 3 * len(q & kw) + 2 * len(q & qs) + 0.5 * len(q & an)
        if score: scored.append((score, f))
    scored.sort(key=lambda x: -x[0])
    if scored:   # drop weak matches so the customer only sees relevant answers
        top = scored[0][0]
        scored = [(sc, f) for sc, f in scored if sc >= 2 and sc >= top * 0.5]
    c.close()
    return dict(faq_page=FAQ_PAGE, matches=[dict(question=f["question"], answer=f["answer"], url=f["page_url"],
                                                 department_id=f["related_department_id"], score=round(s, 1))
                                            for s, f in scored[:limit]])

# ============================================================================ live support
_TOPIC = [("EXP", r"customs|import|duty|duties|international|export|abroad|overseas|vat|gst|border"),
          ("RET", r"return|refund|core|damaged|broken|warranty|defective|exchange it"),
          ("BIL", r"invoice|bill|billing|charged|charge on|payment|pay|currency|exchange rate|credit card|overdue"),
          ("DLR", r"dealer|dealership|wholesale|tier|account terms|bulk")]

def _dept_for(text):
    t = (text or "").lower()
    for dept, pat in _TOPIC:
        if re.search(pat, t): return dept
    return "CS"

def _hours(dept_row, local_dt):
    wd = local_dt.weekday()
    spec = dept_row["weekday_hours"] if wd < 5 else dept_row["saturday_hours"] if wd == 5 else "Closed"
    if spec == "Closed": return None
    a, b = spec.split("-")
    return int(a[:2]), int(b[:2])

def _is_open(dept_row, dt):
    loc = dt.astimezone(HQ_TZ); h = _hours(dept_row, loc)
    return bool(h) and h[0] <= loc.hour < h[1]

def _next_open(dept_row, dt):
    t = dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    while not _is_open(dept_row, t): t += timedelta(hours=1)
    return t

def support_contact(department_id=None, topic=None, customer_timezone="America/New_York", now=None):
    """Phone, email and hours for the right team, whether they're open right now, and when they
    open next - all shown in the customer's own time zone."""
    now = now or NOW
    c = _con()
    dept = (department_id or _dept_for(topic)).upper()
    d = _one(c, "SELECT * FROM support_departments WHERE department_id = ?", dept)
    co = _one(c, "SELECT * FROM company")
    tz = ZoneInfo(customer_timezone)
    fmt = lambda dt: dt.astimezone(tz).strftime("%A %b %d, %I:%M %p").replace(" 0", " ") + f" ({customer_timezone})"
    open_now = _is_open(d, now)
    out = dict(department_id=dept, department=d["department_name"], phone=d["phone"], email=d["email"],
               languages=d["languages"], handles=d["handles"], open_now=open_now,
               hours_central=f'Mon-Fri {d["weekday_hours"]}, Sat {d["saturday_hours"]}, Sun Closed (Central Time)',
               main_phone=co["toll_free_phone"], international_phone=co["international_phone"],
               main_email=co["main_email"], faq_page=FAQ_PAGE)
    if open_now:
        loc = now.astimezone(HQ_TZ); close_h = _hours(d, loc)[1]
        out["closes_at"] = fmt(loc.replace(hour=close_h, minute=0, second=0, microsecond=0))
    else:
        out["next_open"] = fmt(_next_open(d, now))
    c.close()
    return out

_ASK_HUMAN = r"\b(human|person|people|someone|somebody|representative|rep|operator|live (agent|chat|person)|real (person|agent)|talk to|speak (to|with)|call me|customer service)\b"
_ESCALATE = r"\b(complain|complaint|angry|unacceptable|ridiculous|lawyer|legal|sue|chargeback|fraud|scam|manager|supervisor)\b"

def handoff_decision(user_message, bot_confident=True, failed_attempts=0, refund_amount_usd=0.0,
                     customer_timezone="America/New_York", customer_language="English", now=None):
    """Decide whether the bot should connect the customer with a live person. Always returns the
    right team's contact details and the best FAQ answers, so the customer has every option."""
    msg = user_message or ""
    reasons = []
    if re.search(_ASK_HUMAN, msg, re.I): reasons.append("Customer asked for a person")
    if re.search(_ESCALATE, msg, re.I): reasons.append("Complaint or escalation")
    if refund_amount_usd and refund_amount_usd > REFUND_LIMIT_USD: reasons.append("Refund or credit above agent limit")
    if not bot_confident: reasons.append("Agent not confident in its answer")
    if failed_attempts >= MAX_FAILED_ATTEMPTS: reasons.append("Agent could not answer after several tries")
    faq = search_faq(msg, limit=2)["matches"]
    contact = support_contact(topic=msg, customer_timezone=customer_timezone, now=now)
    handoff = bool(reasons)
    interpreter = customer_language not in contact["languages"]
    faq_lines = "".join(f"\n- {m['question']} {m['url']}" for m in faq)
    if handoff:
        # A handoff sends and saves nothing: say who is needed and how to reach them, never that it was passed on.
        when = "They're open now" if contact["open_now"] else f"They're closed and open {contact['next_open']}"
        text = (f"This needs the {contact['department']} team. Not yet sent: nothing has been passed to them. "
                f"{when}: {contact['phone']}, {contact['email']}.")
        if interpreter: text += f" They use an interpreter line for {customer_language}."
        if faq: text += f"\n\nThese FAQ answers may help:{faq_lines}"
        text += f"\n\nFull FAQ: {FAQ_PAGE}"
    else:
        text = (f"These FAQ answers may help:{faq_lines}\n\nFull FAQ: {FAQ_PAGE}\n"
                f"If that doesn't answer it, just say so and I'll give you the right team's contact details.") if faq else \
               f"You can browse our FAQ at {FAQ_PAGE}, or ask me for the right team's contact details."
    return dict(handoff=handoff, reasons=reasons, department_id=contact["department_id"], contact=contact,
                faq_suggestions=faq, interpreter_needed=interpreter, message_to_customer=text,
                case_status="Not yet sent. Offer to open a support case." if handoff else None)

def create_support_case(customer_id, department_id, contact_reason, order_id=None, ai_handoff_reason=None,
                        notes=None, language="English", now=None, db=None):
    """Open a support case for a live person (status Open, or Queued if the team is closed)."""
    now = now or NOW
    c = _con(db)
    d = _one(c, "SELECT * FROM support_departments WHERE department_id = ?", department_id)
    cu = _customer(c, customer_id)
    n = c.execute("SELECT MAX(CAST(substr(case_id, 4) AS INTEGER)) FROM support_cases").fetchone()[0] or 0
    case_id = f"CS-{n + 1:06d}"
    open_now = _is_open(d, now)
    row = dict(case_id=case_id, customer_id=customer_id, order_id=order_id,
               opened_at_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
               opened_at_customer_local=now.astimezone(ZoneInfo(cu["timezone"])).isoformat(timespec="minutes"),
               opened_at_hq_local=now.astimezone(HQ_TZ).isoformat(timespec="minutes"), channel="AI chat handoff",
               ai_handoff_reason=ai_handoff_reason, opened_after_hours=int(not open_now), department_id=department_id,
               contact_reason=contact_reason, language=language,
               priority="High" if cu["customer_type"] == "Dealership" else "Normal", assigned_to=None,
               first_response_at_utc=None, first_response_minutes=None,
               status="Open" if open_now else "Queued (after hours)", resolved_at_utc=None, notes=notes)
    c.execute(f"INSERT INTO support_cases ({','.join(row)}) VALUES ({','.join('?' * len(row))})", tuple(row.values()))
    c.commit(); c.close()
    return dict(case_id=case_id, status=row["status"], department=d["department_name"], phone=d["phone"], email=d["email"])

# ============================================================================ standalone tool definitions
_ITEMS = {"type": "array", "description": "Parts to ship", "items": {"type": "object", "properties": {
    "part_number": {"type": "string"}, "quantity": {"type": "integer", "minimum": 1}}, "required": ["part_number"]}}
TOOL_SCHEMAS = [
    {"name": "get_part_price", "description": "Price of a part for a customer (list price, their price, core charge, local currency at today's rate) and where it's in stock.",
     "input_schema": {"type": "object", "properties": {"part_number": {"type": "string"}, "customer_id": {"type": "string"},
                      "quantity": {"type": "integer"}, "currency": {"type": "string", "description": "ISO code, e.g. CAD"}}, "required": ["part_number"]}},
    {"name": "quote_shipping", "description": "Shipping cost and delivery date for every Parcelora, Velocair, Postara and Globexa Express service that can carry the order, cheapest first, plus services that can't and why.",
     "input_schema": {"type": "object", "properties": {"items": _ITEMS, "ship_to_country": {"type": "string", "description": "ISO country code, default US"},
                      "ship_to_state": {"type": "string", "description": "U.S. state code, required for U.S. addresses"},
                      "residential": {"type": "boolean"}, "customer_id": {"type": "string"}}, "required": ["items"]}},
    {"name": "full_quote", "description": "Everything the customer pays - parts, cores, shipping per carrier, import tax - in their currency.",
     "input_schema": {"type": "object", "properties": {"items": _ITEMS, "customer_id": {"type": "string"},
                      "ship_to_country": {"type": "string"}, "ship_to_state": {"type": "string"}, "residential": {"type": "boolean"}}, "required": ["items"]}},
    {"name": "search_faq", "description": "Find FAQ answers and their links on the FAQ page.",
     "input_schema": {"type": "object", "properties": {"question": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["question"]}},
    {"name": "support_contact", "description": "Phone, email and hours for the right support team, whether it's open now, and when it opens next, in the customer's time zone.",
     "input_schema": {"type": "object", "properties": {"department_id": {"type": "string", "enum": ["CS", "DLR", "EXP", "RET", "BIL"]},
                      "topic": {"type": "string"}, "customer_timezone": {"type": "string", "description": "IANA zone, e.g. America/Toronto"}}}},
    {"name": "handoff_decision", "description": "Call whenever the customer asks for a person, is unhappy, needs a refund over the limit, or you can't confidently answer. Returns whether to hand off, the team, contact details, FAQ links and a message for the customer.",
     "input_schema": {"type": "object", "properties": {"user_message": {"type": "string"}, "bot_confident": {"type": "boolean"},
                      "failed_attempts": {"type": "integer"}, "refund_amount_usd": {"type": "number"},
                      "customer_timezone": {"type": "string"}, "customer_language": {"type": "string"}}, "required": ["user_message"]}},
    {"name": "create_support_case", "description": "Open a case so a live person follows up. Use after handoff_decision says to hand off.",
     "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "department_id": {"type": "string"},
                      "contact_reason": {"type": "string"}, "order_id": {"type": "string"}, "ai_handoff_reason": {"type": "string"},
                      "notes": {"type": "string"}, "language": {"type": "string"}}, "required": ["customer_id", "department_id", "contact_reason"]}},
]
_FUNCS = {f.__name__: f for f in (get_part_price, quote_shipping, full_quote, search_faq, support_contact,
                                   handoff_decision, create_support_case)}

def run_tool(name, args):
    """Run a tool call by name and return a JSON string result."""
    try:
        return json.dumps(_FUNCS[name](**args), default=str)
    except Exception as e:  # report errors back to the model instead of crashing the chat
        return json.dumps({"error": str(e)})

# ============================================================================ demo
def _show(title, obj):
    print(f"\n=== {title}\n" + json.dumps(obj, indent=2, default=str))

def _sample_part(name, make, model, year, brand_type="OEM"):
    c = _con()
    r = c.execute("SELECT DISTINCT p.part_number FROM vehicles v JOIN part_fitment f USING (vehicle_id) JOIN parts p USING (part_id) "
                  "JOIN v_stock_position s ON s.part_id = p.part_id WHERE v.make=? AND v.model=? AND v.year=? AND p.part_name=? "
                  "AND p.brand_type=? AND p.status='Active' AND s.qty_available > 0 LIMIT 1", (make, model, year, name, brand_type)).fetchone()
    c.close()
    return r[0] if r else None

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "demo":
    pads = _sample_part("Brake Pads - Front", "Ferra Motors", "Nivo", 2019)
    _show("Part price for a retail customer", get_part_price(pads))
    q = quote_shipping([{"part_number": pads, "quantity": 1}], "US", "GA")
    _show("Shipping options: brake pads to Georgia", {k: q[k] for k in ("ship_from", "zone", "notes")} |
          {"options": [{k: o[k] for k in ("carrier", "service", "cost_usd", "customer_pays_usd", "estimated_delivery_by")} for o in q["options"]]})
    print("\nFAQ:", json.dumps(search_faq("do you ship to canada and will I pay duties")["matches"][0], indent=2))
    print("\nHandoff:", handoff_decision("I want to talk to a real person about my customs hold",
                                         customer_timezone="Asia/Riyadh")["message_to_customer"])
