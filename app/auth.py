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
    "warehouse":        dict(tabs=["inventory", "orders", "assistant"], cost=False, money=False, customer=False,
                             analytics=False, cases=False, create_cases=False),
    "customer_service": dict(tabs=["inventory", "orders", "assistant", "cases"], cost=False, money=True, customer=True,
                             analytics=False, cases=True, create_cases=True),
    "cs_supervisor":    dict(tabs=["inventory", "orders", "assistant", "cases", "analytics"], cost=False, money=True,
                             customer=True, analytics=True, cases=True, create_cases=True),
    "manager":          dict(tabs=["inventory", "orders", "assistant", "cases", "analytics"], cost=True, money=True,
                             customer=True, analytics=True, cases=True, create_cases=False),
}

# Fields removed from every response unless the role is allowed to see them.
COST_FIELDS = {"unit_cost_usd", "unit_cost_local", "stock_value_usd", "carrier_cost_usd", "shipping_margin_usd",
               "po_value_usd", "po_value_local", "fx_gain_loss_usd", "variance_value_usd", "missing_value_usd",
               "inventory_value_usd"}
MONEY_FIELDS = {"unit_price_usd", "unit_price_local", "line_total_usd", "line_total_local", "order_total_usd",
                "total_due_local", "goods_total_local", "shipping_local", "shipping_usd", "import_tax_local",
                "payment_status", "paid_at_utc", "payment_fx_rate", "payment_terms", "discount_pct", "price_tier",
                "fx_rate_units_per_usd", "fx_margin_pct", "core_charge_usd", "billing_currency", "revenue_usd"}
CUSTOMER_FIELDS = {"customer_name", "primary_vehicle_id", "customer_since"}


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
    """Remove fields this employee isn't allowed to see, at any depth."""
    hidden = set()
    if not emp.perms["cost"]:
        hidden |= COST_FIELDS
    if not emp.perms["money"]:
        hidden |= MONEY_FIELDS
    if not emp.perms["customer"]:
        hidden |= CUSTOMER_FIELDS
    if not hidden:
        return obj

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items() if k not in hidden}
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
