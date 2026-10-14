"""
Gatewell employee app - web server.

    uvicorn app.server:app --port 8000      (from the gatewell_app folder)

Serves the single-page app from app/static and a JSON API under /api. Every API call
identifies the employee (X-Employee-Id header in this prototype), applies their role and
data scope, and redacts fields they aren't allowed to see.
"""
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent_tools as AT
from . import analytics, assistant, db, demo, services
from .auth import ROLE_LABEL, ROLE_OF_TITLE, Employee, current_employee, redact, require

AT.DB_PATH = db.DB_PATH
AT.NOW = db.as_of()
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Gatewell Employee App", version="0.1")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(services.BadInput)
async def bad_input(request: Request, ex: services.BadInput):
    """An unknown filter value (warehouse, status, category): say what's valid instead of returning nothing."""
    return JSONResponse(status_code=400, content={"detail": str(ex)})


@app.middleware("http")
async def demo_visitor_cookie(request: Request, call_next):
    """Give every browser a visitor ID so the demo question limit follows the visitor, not the sample employee."""
    visitor = request.cookies.get(demo.COOKIE)
    new = not visitor
    request.state.visitor = visitor or uuid.uuid4().hex
    response = await call_next(request)
    if new:
        secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie(demo.COOKIE, request.state.visitor, max_age=60 * 60 * 24 * 90, httponly=True,
                            samesite="lax", secure=secure)
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Basic browser protections. Every script, style and font is served by the app itself."""
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy",
                                "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                "object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.headers.get("x-forwarded-proto") == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    """For Railway's health check: the app is up and the database can be read."""
    return {"ok": db.scalar("SELECT COUNT(*) FROM warehouses") == 11}


# --------------------------------------------------------------------------- sign-in (prototype)
@app.get("/api/employees")
def employees():
    """Prototype sign-in list. In production this is replaced by single sign-on."""
    out = []
    for e in db.rows("""SELECT employee_id, first_name || ' ' || last_name name, role title, warehouse_code, region,
                               work_location FROM employees ORDER BY role, warehouse_code"""):
        e["app_role"] = ROLE_LABEL[ROLE_OF_TITLE.get(e["title"], "warehouse")]
        out.append(e)
    return out


@app.get("/api/me")
def me(emp: Employee = Depends(current_employee)):
    co = db.one("SELECT * FROM company")
    return {"employee": emp.public(), "company": co, "as_of": db.as_of().strftime("%Y-%m-%d %H:%M UTC")}


# --------------------------------------------------------------------------- reference data
@app.get("/api/meta")
def meta(emp: Employee = Depends(current_employee)):
    return dict(
        warehouses=db.rows("SELECT warehouse_code, warehouse_name, city, state, region, timezone FROM warehouses ORDER BY warehouse_code"),
        categories=[r["category_group"] for r in db.rows("SELECT DISTINCT category_group FROM parts ORDER BY 1")],
        states=db.rows("SELECT state_code, state_name FROM states ORDER BY state_name"),
        countries=db.rows("SELECT country_code, country_name, currency_code FROM countries ORDER BY country_name"),
        order_statuses=[r["status"] for r in db.rows("SELECT DISTINCT status FROM orders ORDER BY 1")],
        departments=db.rows("SELECT department_id, department_name FROM support_departments"),
        **services.vehicle_options(),
    )


@app.get("/api/vehicles")
def vehicles(make: str | None = None, model: str | None = None, emp: Employee = Depends(current_employee)):
    return services.vehicle_options(make, model)


# --------------------------------------------------------------------------- inventory
@app.get("/api/inventory")
def inventory(q: str | None = None, year: int | None = None, make: str | None = None, model: str | None = None,
              category: str | None = None, warehouse: str | None = None, stock_filter: str | None = None,
              limit: int = 50, emp: Employee = Depends(current_employee)):
    return redact(services.search_inventory(emp, q, year, make, model, category, warehouse, stock_filter, min(limit, 200)), emp)


@app.get("/api/parts/{part_number}")
def part(part_number: str, emp: Employee = Depends(current_employee)):
    d = services.part_detail(emp, part_number)
    if not d:
        raise HTTPException(404, "No part with that number.")
    return redact(d, emp)


@app.get("/api/in-transit")
def transit(warehouse: str | None = None, status: str | None = None, emp: Employee = Depends(current_employee)):
    return redact(services.in_transit(emp, warehouse=warehouse, status=status, limit=100), emp)


class QuoteIn(BaseModel):
    items: list[dict]
    ship_to_country: str = "US"
    ship_to_state: str | None = None
    residential: bool = True
    customer_id: str | None = None


@app.post("/api/quote")
def quote(body: QuoteIn, emp: Employee = Depends(current_employee)):
    q = AT.quote_shipping(body.items, body.ship_to_country, body.ship_to_state, body.residential, body.customer_id)
    if emp.perms["money"] and q.get("ok"):
        q["full_quote"] = AT.full_quote(body.items, body.customer_id, body.ship_to_country, body.ship_to_state, body.residential)
    return redact(q, emp)


# --------------------------------------------------------------------------- orders
@app.get("/api/orders")
def orders(q: str | None = None, status: str | None = None, order_type: str | None = None, warehouse: str | None = None,
           customer_type: str | None = None, days: int | None = None, limit: int = 50,
           emp: Employee = Depends(current_employee)):
    return redact(services.search_orders(emp, q, status, order_type, warehouse, customer_type, days, min(limit, 200)), emp)


@app.get("/api/orders/{order_id}")
def order(order_id: str, emp: Employee = Depends(current_employee)):
    d = services.order_detail(emp, order_id)
    if not d:
        raise HTTPException(404, "No order with that number in your scope.")
    return redact(d, emp)


# --------------------------------------------------------------------------- support cases
@app.get("/api/cases")
def cases(status: str | None = "active", department: str | None = None, q: str | None = None,
          emp: Employee = Depends(current_employee)):
    require(emp, "cases")
    return redact(services.list_cases(emp, status, department, q), emp)


# --------------------------------------------------------------------------- analytics
@app.get("/api/analytics")
def analytics_view(period: str = "90", warehouse: str | None = None, emp: Employee = Depends(current_employee)):
    require(emp, "analytics")
    return redact(analytics.dashboard(emp, period, warehouse), emp)


# --------------------------------------------------------------------------- assistant
class ChatIn(BaseModel):
    messages: list[dict]


@app.post("/api/chat")
def chat(body: ChatIn, request: Request, emp: Employee = Depends(current_employee)):
    if not body.messages or body.messages[-1].get("role") != "user":
        raise HTTPException(400, "Send the conversation ending with the employee's message.")
    if len(body.messages[-1].get("content", "")) > 4000:
        raise HTTPException(400, "That message is too long. Please shorten it.")
    visitor, ip = request.state.visitor, demo.client_ip(request)
    limits = demo.status(visitor, ip)
    if limits["enabled"] and limits["remaining"] <= 0:
        return JSONResponse(status_code=429, content={"detail": demo.limit_message(), "demo": limits})
    try:
        result = assistant.chat(emp, body.messages)
    except assistant.AssistantUnavailable as ex:
        return {"reply": str(ex), "tools_used": [], "handoff": None, "unavailable": True, "demo": limits}
    if result.get("finished"):
        demo.record(visitor, ip)                 # only answered questions count; a reply cut off by the round limit doesn't
    result["demo"] = demo.status(visitor, ip)
    return result


class ConfirmCaseIn(BaseModel):
    proposal_id: str


@app.post("/api/cases/confirm")
def confirm_case(body: ConfirmCaseIn, emp: Employee = Depends(current_employee)):
    """The employee clicked Create case on a case the assistant prepared. This is the only way the chat opens a case."""
    require(emp, "create_cases")
    case = assistant.confirm_case(emp, body.proposal_id)
    if not case:
        raise HTTPException(404, "This case can't be created: it was already created, has expired, or was prepared "
                                 "for someone else. Ask the assistant to prepare it again.")
    return redact(case, emp)


@app.get("/api/demo-status")
def demo_status(request: Request, emp: Employee = Depends(current_employee)):
    return demo.status(request.state.visitor, demo.client_ip(request))


@app.get("/api/assistant/suggestions")
def suggestions(emp: Employee = Depends(current_employee)):
    common = ["Do we have front brake pads for a 2019 Honda Civic in stock?",
              "What's in transit to my warehouse, and is anything delayed?"]
    by_role = {
        "warehouse": ["Which parts in my warehouse need reordering?",
                      "Which orders from my warehouse are still processing, and which bins are the parts in?",
                      "What batteries are on the way to us for winter?"],
        "customer_service": ["A customer in Toronto wants 2 front struts for a 2018 F-150. What's the total in CAD with shipping?",
                             "Compare UPS, FedEx and USPS to ship a bumper cover to Dallas.",
                             "Which support cases are still open, and who has them?"],
        "cs_supervisor": ["How many support cases are open by team, and are any queued after hours?",
                          "Which international orders are held in customs?"],
        "manager": ["What's our shipping cost as a percent of revenue by carrier this quarter?",
                    "Which warehouse has the most missing stock, and in which categories?",
                    "How did the peso drop affect Mexican orders this month?"],
    }
    return {"suggestions": common + by_role[emp.role]}
