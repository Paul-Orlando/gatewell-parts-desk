# Architecture

## The pieces

```
 Browser (employee)                         Server (FastAPI, Python)                       Data
 ┌──────────────────────┐   JSON over HTTP   ┌─────────────────────────────────┐   read-only  ┌──────────────────────┐
 │ Inventory  Orders    │  X-Employee-Id ──▶ │ auth.py   who is this? role,    │ ───────────▶ │ SQLite database      │
 │ Assistant  Cases     │                    │           scope, field redaction│              │ parts, fitment,      │
 │ Analytics            │ ◀── redacted JSON  │ services.py / analytics.py      │              │ inventory, orders,   │
 │ (app.js, Chart.js)   │                    │ agent_tools.py  pricing, rates, │              │ shipments, rates,    │
 └──────────────────────┘                    │                 FAQ, handoff    │ ── one ────▶ │ FAQ, support cases   │
                                             │ assistant.py ──▶ OpenRouter ────┼─▶ Gemini 3.1 Flash-Lite   write path └──────────────────────┘
                                             │   tool loop, system prompt,     │   (support cases only)
                                             │   tools per role, audit log ────┼──▶ logs/assistant_audit.jsonl
                                             └─────────────────────────────────┘
```

**One set of business logic serves both the screens and the assistant.**
- When the Inventory tab shows stock, it calls `services.search_inventory`.
- When the assistant answers "do we have brake pads for a 2019 Nivo?", it calls the same function.
- The same goes for shipping quotes, prices and analytics.

So the assistant can never know more, or say something different, than the screens show.

## A request, step by step

1. **The browser sends the request** with the signed-in employee's ID. In production this becomes a single sign-on token.
2. **`auth.current_employee` loads the employee**, maps their job title to an app role, and works out their data scope:
   - **Warehouse:** their warehouse.
   - **Region:** the warehouses in their region.
   - **Company:** all warehouses.
3. **The service function runs SQL** limited to that scope, on a **read-only** database connection.
4. **`auth.redact` keeps only the fields the role may see,** at any depth of the response. Every field name is classified as public, cost, money or customer; anything unclassified is hidden from restricted roles (it fails closed). Examples: costs and margins for non-managers; customer prices, shipping charges, totals and payments for warehouse staff; customer names for warehouse staff. The public list price is visible to everyone.
5. **The response goes back to the browser.**

## The assistant

`assistant.chat()` runs the model's tool-use loop. The model is Gemini 3.1 Flash-Lite through OpenRouter's OpenAI-compatible API, and the only model-specific code is the small `OpenRouterClient` in `assistant.py`.

1. **Build the system prompt.** It covers who the employee is, their role and scope, what they can't see, the data's as-of time, how to answer, and when to bring in a person.
2. **Offer only the tools this role may use.** For example, warehouse staff don't get `full_quote` or `analytics_summary`, and only customer service can `propose_support_case`.
3. **For each tool the model asks for,** run it as this employee, redact the result for their role, and cap its size by dropping whole rows (with a `_shortened` note; counts and totals still cover everything). Then send the result back. Unknown filter values (a warehouse, status or category the data doesn't have) come back as an error listing the valid choices, never as an empty result. Tool schemas give the model the valid values up front: warehouse codes and analytics section names are enums, and the system prompt lists every warehouse with its city.
4. **Stop** when the model answers, or after 8 rounds. If OpenRouter fails, retry once, then show a clear "assistant unavailable" message; the other tabs keep working.
5. **Write an audit record:** employee, role, model, question, tools used, whether it handed off, tokens, and time taken.

In the demo version, `demo.py` allows 5 answered questions per visitor, counted on the server.

| Tool | Purpose | Roles |
|---|---|---|
| `search_inventory` | Parts and stock by text, vehicle, category, warehouse, low/out/missing/aged | All |
| `get_part_details` | Specs, fitment, stock and bins per warehouse, inbound, equivalents, sales | All |
| `find_in_transit` | Inbound shipments, ETAs, delays, customs holds | All |
| `search_orders`, `get_order` | Order lookup within scope | All |
| `get_part_price` | List price, customer price, core charge, local currency | All (customer prices redacted for warehouse) |
| `quote_shipping` | Every carrier's price and delivery date, plus what can't ship and why | All |
| `full_quote` | Parts + cores + shipping + import tax in the customer's currency | CS, CS supervisor, managers |
| `list_support_cases` | Cases by status, team, customer | CS, CS supervisor, managers |
| `analytics_summary` | Metrics for the employee's scope | CS supervisor, managers |
| `search_faq` | Policy answers with links | All |
| `contact_team` | A team's phone, email, hours, open now / next opening in local time | All |
| `escalate_to_person` | Hand off: the right team, how to reach them, FAQ links | All |
| `propose_support_case` | Prepare a case for a specialist to follow up. Nothing is saved until the employee clicks Create case in the chat | CS, CS supervisor |

The assistant has **no** tool that changes inventory, orders, prices, refunds or payments.

## Shipping rate engine

`agent_tools._service_cost` prices one service in four steps:

1. **Packages:** small parts share a box; larger parts go several to a carton, up to 50 lb.
2. **Billable weight:** the greater of actual and dimensional weight.
3. **Base charge:** the zone rate, minus the negotiated discount.
4. **Extras:** surcharges (residential, additional handling, large package, hazmat, Postara nonstandard length), then fuel as a percentage on top.

The rule checks are separate. Each one rules out a service and records why:
- weight and size limits
- batteries ground only
- no batteries overseas

The data generator uses the **same engine** to estimate what each historical order cost us to ship. That way analytics and live quotes always agree.

To go live, replace `_service_cost` with calls to the carriers' rating APIs. Everything that calls it keeps working.

## Data

Read `docs/DATA_DICTIONARY.md` for every table. The main ones are:
- `parts`, `part_fitment`, `vehicles`
- `inventory`, plus the view `v_stock_position` (every stock bucket per part per warehouse)
- `orders`, `order_lines`
- `shipments`, plus the view `v_in_transit`
- `customers`, `employees`
- `support_cases`, `faq`
- `shipping_*` (rate cards)
- `currencies`, `exchange_rates`

## Moving from prototype to production

| Prototype | Production |
|---|---|
| Pick-an-employee sign-in | Company single sign-on (e.g. Okta, Microsoft Entra ID); roles from directory groups |
| SQLite snapshot | Read replica or API of the real warehouse management and ERP systems |
| Synthetic rate cards | The parcel carriers' rating APIs with the company's account |
| Synthetic exchange rates | Daily feed (e.g. Federal Reserve H.10 or ECB reference rates) |
| Audit log file | Central logging with retention rules and review dashboards |
| One server process | Railway service with a volume at `/data`, health check at `/api/health`, HTTPS, and monitoring |
