"""
Who can see what.

Every employee maps to one app role. The role decides which tabs they see and which fields
are removed from anything the app or the assistant returns. Their data scope (Warehouse,
Region or Company, from the employees table) decides which warehouses' orders and analytics
they can see. All of this is enforced on the server, never only in the browser.

Prototype sign-in: the browser sends the employee ID in the X-Employee-Id header.
Production: replace current_employee() with your company's single sign-on (SSO).
"""
from dataclasses import dataclass, field

from fastapi import Header, HTTPException

from . import db

ROLE_OF_TITLE = {
    "Warehouse Associate": "warehouse",
    "Inventory Control Specialist": "warehouse",
    "Customer Service Rep": "customer_service",
    "Customer Service Supervisor": "cs_supervisor",
    "Warehouse Manager": "manager",
    "Regional Manager": "manager",
    "Purchasing Analyst": "manager",
    "Operations Director": "manager",
}

ROLE_LABEL = {
    "warehouse": "Warehouse",
    "customer_service": "Customer Service",
    "cs_supervisor": "Customer Service Supervisor",
    "manager": "Management",
}

# What each role may do. "cost" = our costs and margins; "money" = customer prices, totals and payments;
# "customer" = customer names and contact details.
PERMISSIONS = {
    "warehouse":        dict(tabs=["inventory", "orders", "assistant", "teams"], cost=False, money=False, customer=False,
                             analytics=False, cases=False, create_cases=False),
    "customer_service": dict(tabs=["inventory", "orders", "assistant", "cases", "teams"], cost=False, money=True, customer=True,
                             analytics=False, cases=True, create_cases=True),
    "cs_supervisor":    dict(tabs=["inventory", "orders", "assistant", "cases", "teams", "analytics"], cost=False, money=True,
                             customer=True, analytics=True, cases=True, create_cases=True),
    "manager":          dict(tabs=["inventory", "orders", "assistant", "cases", "teams", "analytics"], cost=True, money=True,
                             customer=True, analytics=True, cases=True, create_cases=False),
}

# Every field name the app returns is classified into exactly one of four groups. PUBLIC_FIELDS are visible to
# every role; the other three need the matching permission. A field in no group is hidden from any role that
# lacks a permission (it fails closed), and tests/test_permissions.py fails until a new field is classified.
# The public list price (list_price_usd) stays visible to everyone; a customer's own price does not.
COST_FIELDS = {"unit_cost_usd", "unit_cost_local", "stock_value_usd", "carrier_cost_usd", "shipping_margin_usd",
               "po_value_usd", "po_value_local", "fx_gain_loss_usd", "variance_value_usd", "missing_value_usd",
               "inventory_value_usd",
               # shipping estimate for a suggested transfer (recommend.py)
               "estimated_cost_usd",
               # figures worked out from our costs (analytics)
               "avg_cost_pct_of_list", "avg_carrier_cost_usd", "cost_pct_of_revenue", "shipping_cost_pct_of_revenue"}
MONEY_FIELDS = {"unit_price_usd", "unit_price_local", "line_total_usd", "line_total_local", "order_total_usd",
                "total_due_local", "goods_total_local", "shipping_local", "shipping_usd", "import_tax_local",
                "payment_status", "paid_at_utc", "payment_fx_rate", "payment_terms", "discount_pct", "price_tier",
                "fx_rate_units_per_usd", "fx_margin_pct", "core_charge_usd", "billing_currency", "revenue_usd",
                # a customer's price and core charge (get_part_price)
                "subtotal_usd", "subtotal_local", "core_charge_local",
                # shipping charges (quote_shipping): totals and the per-package breakdown
                "cost_usd", "cost_local", "customer_pays_usd", "transportation_usd", "fuel_surcharge_usd",
                "package_total_usd", "surcharges",
                # a customer's total (full_quote), only offered to roles with prices but classified here too
                "full_quote", "parts", "shipping", "import_tax", "core_charges",
                # sales figures (analytics)
                "avg_order_value_usd", "avg_charged_usd", "billed_local", "domestic_revenue_usd",
                "international_revenue_usd", "international_revenue_pct"}
CUSTOMER_FIELDS = {"customer_name", "primary_vehicle_id", "customer_since"}
PUBLIC_FIELDS = {
    # parts and fitment
    "part", "part_id", "part_number", "part_name", "brand", "brand_type", "quality_tier", "condition", "category",
    "category_group", "position", "oem_family", "fits", "fits_key", "fits_scope", "fits_summary", "make", "model",
    "engines", "year_from", "year_to", "status", "superseded_by_part_id", "supersession_date", "replacement",
    "equivalents", "equivalent_parts", "list_price_usd", "note", "found", "hazmat", "hazmat_note", "size_class",
    "shipping_class", "weight_lb", "weight_kg", "length_cm", "width_cm", "height_cm", "primary_supplier_id",
    "supplier", "supplier_name", "city", "country", "state", "region", "timezone",
    # stock
    "stock_by_warehouse", "warehouse", "warehouses", "warehouse_code", "warehouse_city", "warehouse_state",
    "bin_location", "qty_on_hand", "qty_available", "qty_reserved", "qty_in_transit", "qty_backordered",
    "qty_missing", "qty_damaged", "reorder_point", "reorder_qty", "avg_daily_demand", "needs_reorder",
    "days_since_last_activity", "days_of_cover", "last_received_utc", "last_sold_utc", "last_counted_utc",
    "warehouses_needing_reorder", "warehouses_stocking", "in_stock_total", "totals", "on_hand", "available",
    "missing", "backordered", "monthly_sales", "order_month", "units",
    # inbound shipments
    "in_transit", "shipments", "shipment_id", "shipment_type", "po_number", "transfer_number", "origin_name",
    "origin_city", "origin_country", "destination_warehouse", "mode", "carrier", "port_of_entry",
    "ship_date_origin_local", "eta_destination_local", "exception_note", "currency", "lines", "quantity",
    "total_units",
    # orders
    "order", "order_id", "customer", "customer_id", "customer_type", "franchise_make", "order_type", "channel",
    "ordered_at_utc", "ordered_at_local", "shipped_at_utc", "delivered_at_utc", "delivered_at_local",
    "customer_timezone", "fulfillment_warehouse", "ship_to_city", "ship_to_state", "ship_to_region",
    "ship_to_country", "ship_to_country_code", "ship_mode", "carrier_service", "carrier_service_code",
    "tracking_number", "customs_status", "export_documents", "incoterm", "import_tax_name", "import_tax_pct",
    "import_tax_paid_by", "fx_rate_date", "line_no", "line_status", "core_status", "for_vehicle",
    "country_of_origin", "hs_code", "usmca_eligible", "support_cases",
    # shipping quotes
    "ok", "message", "faq", "ship_from", "ship_to", "zone", "residential", "package_count", "total_weight_lb",
    "options", "service", "service_code", "speed", "transit_business_days", "ships_on", "estimated_delivery_by",
    "stock_status", "available_at_ship_from", "next_inbound", "eta_local", "delivery", "all_in_stock",
    "delivery_by", "packages", "package", "billable_weight_lb", "dimensions_in", "unavailable", "reason",
    "notes", "disclaimer",
    # support cases, teams, FAQ and handoffs
    "case_id", "opened_at_utc", "opened_at_customer_local", "opened_at_hq_local", "ai_handoff_reason",
    "opened_after_hours", "department", "department_id", "department_name", "contact_reason", "language",
    "priority", "assigned_to", "assigned_name", "first_response_at_utc", "first_response_minutes",
    "resolved_at_utc", "status_counts", "n", "proposal_id", "expires_in_minutes", "contact", "phone", "email",
    "languages", "handles", "open_now", "closes_at", "next_open", "hours_central", "main_phone",
    "international_phone", "main_email", "faq_page", "matches", "question", "answer", "url", "score", "handoff",
    "reasons", "reason_given", "faq_suggestions", "interpreter_needed", "message_to_customer", "case_status", "next_step",
    "teams", "hours",
    # analytics layout and stock figures (money and cost figures are classified above)
    "period", "scope", "scope_note", "as_of", "as_of_display", "stock_as_of", "section_totals", "missing_by_warehouse", "how_to_read", "partial", "cancelled_orders", "next_open_customer_local", "closes_at_customer_local",
    "skus_missing", "period_covers", "section_notes", "kpis", "label", "orders",
    "units_on_hand", "units_available",
    "units_in_transit", "units_missing", "units_backordered", "units_sold", "skus_needing_reorder",
    "skus_out_of_stock", "skus_stocked", "inventory_by_group", "inventory_by_warehouse", "low_stock",
    "missing_by_group", "missing_by_warehouse_group", "stock_aging", "sales_by_month", "sales_by_quarter", "first_order_date",
    "last_order_date", "sales_by_group", "revenue_by_region",
    "revenue_by_country", "top_parts", "price_by_group", "oem_avg_price_usd", "premium_avg_price_usd",
    "value_avg_price_usd", "shipping_by_carrier", "shipping_by_service",
    # suggested actions (recommend.py); the transfer shipping estimate is a cost field
    "for_warehouse", "need_now", "transfer_options", "spare_qty", "suggested_qty", "transit_days", "reorder",
    "covered_by_inbound", "lead_time_days", "next_eta_local", "substitutes", "summary", "suggestion",
    "recommendations",
    # result framing
    "count", "total", "results", "_shortened",
}
# Fields whose value is a map keyed by data (e.g. surcharge name -> amount): classified as a whole, not walked.
OPAQUE_FIELDS = {"surcharges"}


@dataclass
class Employee:
    employee_id: str
    name: str
    title: str
    role: str
    scope: str                      # Warehouse | Region | Company
    warehouse_code: str | None
    region: str | None
    languages: str
    perms: dict = field(default_factory=dict)

    def warehouses(self) -> list[str] | None:
        """Warehouse codes this employee's data scope covers (None = all)."""
        if self.scope == "Company":
            return None
        if self.scope == "Warehouse" and self.warehouse_code:
            return [self.warehouse_code]
        if self.scope == "Region" and self.region:
            return [r["warehouse_code"] for r in db.rows("SELECT warehouse_code FROM warehouses WHERE region = ?", self.region)]
        return None

    def public(self) -> dict:
        return dict(employee_id=self.employee_id, name=self.name, title=self.title, role=self.role,
                    role_label=ROLE_LABEL[self.role], scope=self.scope, warehouse_code=self.warehouse_code,
                    region=self.region, languages=self.languages, tabs=self.perms["tabs"],
                    can_see_cost=self.perms["cost"], can_see_money=self.perms["money"],
                    can_see_customer=self.perms["customer"], scope_label=self.scope_label())

    def scope_label(self) -> str:
        if self.scope == "Company":
            return "All warehouses"
        if self.scope == "Region":
            return f"{self.region} region"
        return f"{self.warehouse_code} warehouse"


def load_employee(employee_id: str) -> Employee | None:
    e = db.one("SELECT * FROM employees WHERE employee_id = ?", employee_id)
    if not e:
        return None
    role = ROLE_OF_TITLE.get(e["role"], "warehouse")
    scope = e["chat_access_scope"]
    if role in ("customer_service", "cs_supervisor"):
        scope = "Company"           # customer service helps customers of every warehouse
    return Employee(employee_id=e["employee_id"], name=f'{e["first_name"]} {e["last_name"]}', title=e["role"],
                    role=role, scope=scope, warehouse_code=e["warehouse_code"], region=e["region"],
                    languages=e["languages"], perms=PERMISSIONS[role])


def current_employee(x_employee_id: str | None = Header(default=None)) -> Employee:
    """FastAPI dependency: who is making this request."""
    if not x_employee_id:
        raise HTTPException(401, "Please sign in.")
    emp = load_employee(x_employee_id)
    if not emp:
        raise HTTPException(401, "Unknown employee.")
    return emp


def require(emp: Employee, permission: str) -> None:
    if not emp.perms.get(permission):
        raise HTTPException(403, f"Your role ({ROLE_LABEL[emp.role]}) doesn't have access to this.")


def redact(obj, emp: Employee):
    """Keep only the fields this employee may see, at any depth. Roles with every permission see everything;
    for anyone else a field must be public or in a group they're allowed, so an unclassified field is hidden."""
    p = emp.perms
    if p["cost"] and p["money"] and p["customer"]:
        return obj
    allowed = set(PUBLIC_FIELDS)
    if p["cost"]:
        allowed |= COST_FIELDS
    if p["money"]:
        allowed |= MONEY_FIELDS
    if p["customer"]:
        allowed |= CUSTOMER_FIELDS

    def walk(o):
        if isinstance(o, dict):
            return {k: (v if k in OPAQUE_FIELDS else walk(v)) for k, v in o.items() if k in allowed}
        if isinstance(o, list):
            return [walk(v) for v in o]
        return o
    return walk(obj)


def scope_sql(emp: Employee, column: str) -> tuple[str, list]:
    """SQL fragment limiting rows to the employee's warehouses, e.g. (' AND o.fulfillment_warehouse IN (?,?)', [...])."""
    whs = emp.warehouses()
    if whs is None:
        return "", []
    return f" AND {column} IN ({','.join('?' * len(whs))})", whs
