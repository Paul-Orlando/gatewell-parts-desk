# Gatewell Auto Parts Co. — Synthetic Inventory Dataset

A realistic, **100% synthetic and royalty-free** dataset for prototyping a warehouse inventory AI agent for auto parts.
It covers domestic and international orders, multiple currencies, and live customer-service handoff.
You own it. Use, change and share it without restriction.

- **As-of time:** 2026-10-11 21:00 UTC (5:00 PM Eastern / 4:00 PM Central)
- **History:** 2025-01-01 → 2026-10-11 (about 21 months). The generator simulates from October 2024, then keeps closed orders and delivered shipments from January 2025 on, which holds the file to about 43 MB. Open invoices and everything in transit are always kept.
- **Files:** `car_parts_inventory.db` (SQLite, all tables plus views), `car_parts_dataset_csv.zip` (one CSV per table), `generate_dataset.py` (regenerates everything; the same seed gives identical data on every run), `agent_tools.py` (the agent's tools: prices, shipping quotes, FAQ, live-person handoff)

> **Important.** Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers. Year, body type and engine combinations approximate common U.S. vehicles, but every make, model, brand, carrier and part number is invented (see `data_generator/name_map.py`).
> Gatewell Auto Parts and all companies, vehicles, brands, carriers, people, orders, prices and rates in this demo are fictional. Any resemblance to real products or companies is coincidental. Place names and currencies are real.
> Part numbers follow realistic manufacturer formats and could coincidentally match a real number. **Never use them for real ordering.**

## The company (fictional)

| | |
|---|---|
| **Name** | Gatewell Auto Parts Co. |
| **Headquarters** | 1400 Confluence Way, Suite 200, St. Louis, MO 63102, United States |
| **Customer service, toll-free (U.S. & Canada)** | (800) 555-0142 |
| **Calling from outside the U.S. & Canada** | +1 (314) 555-0142 |
| **Email** | support@gatewellautoparts.example |
| **Website** | www.gatewellautoparts.example |

Phone numbers use the **555-0100 to 555-0199** range reserved for fictional use. The **.example** domain is reserved too, so neither can ever reach a real business. Swap in real details once you register them.

### Support departments (`support_departments`)

Hours are U.S. **Central Time** (`America/Chicago`). The agent converts them to the caller's own time zone.

| Department | Phone | Email | Mon–Fri | Sat | Languages |
|---|---|---|---|---|---|
| Customer Service | (800) 555-0142, option 1 | support@… | 7:00–19:00 | 8:00–14:00 | English, Spanish |
| Dealer Accounts | (800) 555-0143 | dealers@… | 7:00–18:00 | Closed | English, Spanish |
| International & Export Desk | +1 (314) 555-0144 | export@… | 7:00–17:00 | Closed | English, Spanish, French, Arabic |
| Returns & Cores | (800) 555-0145 | returns@… | 8:00–17:00 | 8:00–12:00 | English, Spanish |
| Billing & Currency | (800) 555-0146 | billing@… | 8:00–17:00 | Closed | English, Spanish, French |

All emails end in `@gatewellautoparts.example`. Sunday is closed for every department.

### Live-person handoff (`support_cases`)

`support_cases` has 1,042 contacts from three channels: **AI chat handoff**, **Phone** and **Email**. Each case records:
- the open time in the customer's local time and in HQ local time, and whether it came in after hours
- department, contact reason, language and priority
- the rep assigned (matched by department and language) and first-response time
- status, and why the AI handed off (for example the customer asked for a person, or the refund was over the agent's limit)

**Handoff rules the agent should follow:**
1. Hand off when the customer asks for a person, the agent isn't confident about fitment, a refund or credit is over its limit, or there's a complaint.
2. Route by reason:
   - Fitment and order status → Customer Service
   - Dealer pricing and accounts → Dealer Accounts
   - Customs and international orders → Export Desk
   - Returns and cores → Returns & Cores
   - Invoices and currency → Billing & Currency
3. If the department is open, connect now. If it's closed, open a case marked **Queued (after hours)** and tell the customer when the department opens, in *their* local time.
4. Always show the department's phone number and email as a fallback.

Customer-service reps (`employees`, role *Customer Service Rep*) work at St. Louis HQ and list their languages.

### When the bot hands off to a live person

The bot (see `agent_tools.py`, `handoff_decision`) hands off when **any** of these is true:

- The customer asks for a person ("talk to someone", "representative", "real person"…).
- The customer is unhappy or escalating (complaint, chargeback, wants a manager…).
- A refund or credit is over **$250**, the most the bot can promise.
- The bot isn't confident in its answer, for example on fitment.
- The bot has failed to answer **2 times** in a row.

**When it hands off,** the bot always tells the customer three things:
1. Which team will help.
2. Whether that team is open right now, or when it opens, in the customer's time zone.
3. The team's phone number and email.

It then opens a support case. The case is **Open** if the team is working, or **Queued (after hours)** if not.

**Every time, handoff or not, the bot also links the 1–2 FAQ answers that best match the question, plus the full FAQ page** (`https://www.gatewellautoparts.example/faq`). If the FAQ already answers the question, the bot offers it first and says it can connect a person if that doesn't help.

## FAQ (`faq`)

25 answers in 10 groups:
- finding the right part
- ordering and pricing
- shipping and delivery
- international orders
- currency and payment
- returns and cores
- warranty
- dealer accounts
- contacting us
- location

Each answer has search keywords, the team that owns the topic, and its anchor link on the FAQ page (for example `…/faq#what-is-a-core-charge`). The policies in the answers are consistent with the data:
- 30-day returns
- core refunds
- free ground shipping over $99 (oversize parts excluded)
- 3:00 PM same-day cutoff
- no batteries overseas
- 2% currency conversion margin

**These policies are fictional; replace them with your real ones.**

## Shipping costs by carrier

The bot can quote **every major carrier**, cheapest first, with an estimated delivery date for each service.

| Carrier | Domestic | International |
|---|---|---|
| **Parcelora** | Ground, 2-Day, Next Day | Standard (Canada & Mexico), Worldwide Expedited, Worldwide Express |
| **Velocair** | Ground, 2Day, Overnight | International Ground (Canada), International Economy, International Express |
| **Postara** | Ground Saver, Priority, Priority Overnight | Priority International |
| **Globexa Express** | (international only from the U.S.) | Express Worldwide |

**How a quote is built** (`quote_shipping`):

1. **Pick the warehouse.** Use the one that serves the destination. If it's out of stock, use the warehouse with the most stock, and say so.
2. **Pack the order.** Small parts share one box; each larger part ships in its own box.
3. **Work out the billable weight.** Billable weight = the greater of actual weight and **dimensional weight** (L×W×H ÷ 139 for Parcelora/Velocair/Globexa Express, ÷ 166 for Postara over 1 cubic foot).
4. **Price each service.** Price = zone rate (first pound + each additional pound) + surcharges + fuel surcharge (a percentage).
   - Surcharges are residential delivery, additional handling (over 48 in or 50 lb), large package (length + girth over 130 in), hazmat ground fee, and Postara nonstandard length.
5. **Rule out services that can't carry it**, and say why. For example:
   - Lead-acid batteries go by **Parcelora/Velocair ground only**.
   - Postara can't take a bumper cover (too large).
   - Postara has a 70 lb limit.
6. **Estimate the delivery date.** Orders before **3:00 PM warehouse time** on a business day ship that day; transit days are added on business days.
7. **Convert to the customer's currency** at today's rate.
8. **Apply free ground shipping** for dealers and for U.S. individual orders of $99+, except oversize parts.

`full_quote` adds it all up for the customer:
- the part price at their account's pricing
- core charges
- shipping for each carrier
- import tax (VAT/GST) for international individuals, which we collect at checkout

The result is a total for each carrier option, in the customer's currency.

> **All rates, surcharges and transit times are synthetic estimates.** For live pricing, connect each parcel carrier's rating API (major carriers offer one with a business account) and replace `_service_cost()` in `agent_tools.py`.

### What shipping actually costs us

Every order records `carrier_cost_usd`, our estimated cost from the same rate engine the agent uses, next to `shipping_usd`, what the customer was charged. `shipping_margin_usd` is the difference.

The estimate assumes three things:
- **Negotiated rates.** A 45% contract discount off carrier transportation charges, which is typical for a distributor this size (synthetic).
- **Cartons.** Several units of the same part share a box, up to 50 lb.
- **Dealer freight.**
  - Nearby dealers (zones 2–3) usually get our own **Gatewell Delivery** route truck.
  - Overseas dealers ship by **freight forwarder**, as consolidated air or ocean freight.

Overall, shipping costs about **11% of revenue**. Most of that is absorbed through free shipping and dealer delivery. International shipping is passed through to customers at cost plus 5%.

## Agent tools (`agent_tools.py`)

The first working piece of the chat agent. Each function returns JSON, and `TOOL_SCHEMAS` holds ready-made tool definitions for Claude.

| Tool | What it does |
|---|---|
| `get_part_price` | Part price for the customer's account, core charge, local currency, stock by warehouse, equivalent parts |
| `quote_shipping` | Every carrier's price and delivery date, plus services that can't carry the order and why |
| `full_quote` | Parts + cores + shipping + import tax, per carrier, in the customer's currency |
| `search_faq` | Best FAQ answers with page links |
| `support_contact` | Right team's phone, email, hours, open now or next opening, in the customer's time zone |
| `handoff_decision` | Whether to connect a live person, which team, and the message to show the customer |
| `create_support_case` | Opens the case for the live person |

Run `python3 agent_tools.py demo` to see example output.

## What's inside

| Table | Rows | What it holds |
|---|---:|---|
| `company` | 1 | Name, HQ address, phone numbers, email, website |
| `support_departments` | 5 | Phone, email, hours (Central), languages, what each one handles |
| `faq` | 25 | FAQ questions and answers, each with its link on the FAQ page and the team that owns it |
| `shipping_services` | 20 | Parcelora, Velocair, Postara and Globexa Express services, plus our own dealer delivery routes and freight forwarders: limits, hazmat rules, transit times |
| `shipping_rates` | 95 | Price per zone: first pound and each additional pound (synthetic estimates) |
| `shipping_surcharges` | 22 | Fuel, residential, additional handling, large package, hazmat, Postara nonstandard length |
| `shipping_zones_domestic` | 561 | Shipping zone (2–8) from every warehouse to every state |
| `support_cases` | 1,042 | Contacts with live people, including AI chat handoffs |
| `vehicles` | 1,061 | Year / make / model / engine for 62 common U.S. models, 2010–2026, 14 makes |
| `platforms` | 160 | Model generations (about 6-year spans) that share chassis parts |
| `parts` | 10,150 | OEM and aftermarket parts in 24 categories: type, position, size, weight, hazmat, core charge, supersession |
| `part_fitment` | 86,231 | Which part fits which vehicle |
| `part_interchange` | 5,936 | Aftermarket ↔ OEM cross-references, plus old ↔ new OEM numbers |
| `warehouses` | 11 | One in every U.S. time zone, from Newark to Honolulu |
| `states` | 51 | Region, time zone, serving warehouse, climate, road-salt flag |
| `countries` | 13 | U.S. plus 12 export markets: currency, VAT/GST, serving warehouses, delivery times |
| `currencies` | 16 | Code, symbol, decimal places, whether it's pegged to the dollar |
| `exchange_rates` | 10,384 | Daily rate for every currency (units per USD and USD per unit) |
| `suppliers` | 8 | Japan, South Korea, China, Germany, Mexico (2), Canada, U.S. |
| `customers` | 5,959 | 259 dealerships (199 U.S., 60 international) and 5,700 individuals (5,000 U.S., 700 international) |
| `orders` / `order_lines` | 28,251 / 64,709 | Sales since January 2025, 3,608 of them international, each with carrier, service, tracking number and our estimated carrier cost |
| `shipments` / `shipment_lines` | 2,936 / 44,798 | Supplier POs (priced in the supplier's currency) and warehouse transfers |
| `inventory` | 14,344 | Current stock per part per warehouse in every quantity bucket |
| `cycle_counts` | 10,452 | Physical counts vs. system counts. This is where "missing" comes from. |
| `employees` | 87 | Roles (including an Operations Director with company-wide access), location, languages, support department, chat access scope |

### Views (ready-made for the agent)

- **`v_stock_position`:** one row per part per warehouse, with all quantity buckets, `qty_available`, `needs_reorder`, stock value, and days since last activity.
- **`v_sales`:** units sold, domestic and international, with the local-currency and USD amounts.
- **`v_in_transit`:** everything currently moving, including origin country, ports, ETAs in local time, and supplier currency.
- **`v_movements`:** an audit trail built from receipts, sales, customer returns and count adjustments.
- **`v_fx_latest`:** today's rate for every currency.
- **`v_receivables`:** unpaid invoices valued at today's rate, with the unrealized exchange gain or loss.

## Domestic and international orders

`orders.order_type` is **Domestic** or **International**. International orders ship to 12 markets:

| Market | Countries (currency) | Ships from |
|---|---|---|
| North America | Canada (CAD), Mexico (MXN) | Columbus, Newark, Chicago, Seattle, Dallas, Inland Empire |
| Latin America & Caribbean | Dominican Republic (DOP), Costa Rica (CRC), Colombia (COP), Chile (CLP) | Atlanta |
| Europe | United Kingdom (GBP), Germany (EUR) | Newark |
| Middle East | Saudi Arabia (SAR), United Arab Emirates (AED) | Newark |
| Asia-Pacific | Australia (AUD), Philippines (PHP) | Inland Empire (CA) |

Each international order carries:
- **Ship mode:**
  - Canada and Mexico: cross-border truck (dealers) or parcel (individuals)
  - Overseas: air parcel, air freight, or consolidated ocean
- **Incoterm:**
  - **DAP** for dealers: they pay import tax when the goods arrive.
  - **DDP** for individuals: we collect import tax at checkout.
- **Import tax:** the country's standard VAT/GST rate, which is a simplification. Verify real rates before go-live.
- **Customs status:** Not shipped, In transit to border/port, Awaiting clearance, Cleared, or **Held – missing documents**.
- **Export documents:**
  - A commercial invoice on every order.
  - A **USMCA certification of origin** when every part on a Canada or Mexico order was made in the U.S., Canada or Mexico.
  - **EEI filed in AES** on orders over $2,500.
- **Per line:** country of origin, an indicative **HS code** (verify with a customs broker), and a USMCA-eligibility flag.

**Business rule:** lead-acid batteries (hazmat) are not exported overseas.

Seasonal demand follows the customer's own climate. Southern-hemisphere countries (Chile, Australia) have their seasons flipped, so their cooling-system demand peaks in December–February.

## Currencies and exchange rates

- **16 currencies:** 13 for customers, plus JPY, KRW and CNY for supplier purchase orders.
  - Decimal places follow the currency: Chilean pesos, yen and won have none.
  - The Saudi riyal (3.75) and UAE dirham (3.6725) are pegged to the dollar.
- **Every money amount is stored twice:**
  - in the transaction currency (`..._local`)
  - in **USD at that day's rate** (`..._usd`), with the rate used (`fx_rate_units_per_usd`)
- **Billing currency:**
  - Individuals pay in their own currency.
  - International dealers are billed in either their local currency or USD (`customers.billing_currency`).
  - Local-currency invoices include a 2% conversion margin (`fx_margin_pct`).
- **Payments:**
  - Card and prepaid orders are paid at the time of order.
  - Net 15 and Net 30 dealer invoices are paid later, at that day's rate.
  - The difference is the **realized exchange gain or loss** (`orders.fx_gain_loss_usd`).
  - Unpaid invoices show their **unrealized** gain or loss in `v_receivables`.
- **Supplier POs** are priced in the supplier's currency: JPY, KRW, CNY, EUR, MXN, CAD or USD.

> **The rates are synthetic** (a realistic random walk). For live rates, two free sources are the U.S. Federal Reserve's H.10 daily rates and the European Central Bank's euro reference rates. Load them into `exchange_rates` with the same columns.

## Quantity buckets (how "on hand, in transit, sold, missing" are defined)

| Bucket | Meaning |
|---|---|
| `qty_on_hand` | Units the system says are in the building |
| `qty_reserved` | On hand but committed to orders still processing |
| `qty_damaged` | On hand but not sellable |
| `qty_missing` | Units the most recent cycle count couldn't find, still under review (not yet written off) |
| `qty_available` | on hand − reserved − damaged − missing (never below 0) |
| `qty_in_transit` | On an inbound shipment with status In Transit, Delayed or Customs Hold |
| `qty_backordered` | Ordered by customers but not fillable yet |
| **Sold** | Sum of `quantity` in `v_sales` (shipped, delivered or returned lines) |

## Dates and time zones

- Every timestamp is stored in **UTC** (`..._utc`, ISO 8601 with `Z`).
- The matching **local time with its offset** is stored next to it:
  - `ship_date_origin_local = 2026-09-05T17:59+08:00` (Ningbo)
  - `eta_destination_local = 2026-10-04T19:12-07:00` (California)
  - `opened_at_customer_local` and `opened_at_hq_local` on support cases
- Time zones are IANA names (`America/Phoenix`, `Pacific/Honolulu`, `Asia/Riyadh`, `Australia/Perth`…). This handles places without daylight saving time automatically.

## Built-in scenarios (so demo questions have real answers)

1. **Shrinkage at Newark (NWK):** small, high-value parts (O2 sensors, ignition coils, spark plugs, ABS sensors) keep coming up short in cycle counts. NWK has far more missing units than any other warehouse.
2. **Customs hold:** 5 inbound shipments from Ningbo, China are held by U.S. Customs at Long Beach, Houston and Seattle-Tacoma, past their ETAs.
3. **Winter battery prep:** battery transfers are in transit to cold-climate warehouses (Chicago, Columbus, Newark, Denver, Anchorage), whose battery stock is running low.
4. **Backorders at Atlanta:** a front brake pad for the 2019–2024 Ironhorn 2500 (part IH-100009) is out of stock at ATL, with backorders, open "Backorder ETA" support cases (several queued for Monday because it's Sunday at HQ), and an expedited air shipment due Oct 14.
5. **Peso slide:** the Mexican peso weakened about 9% against the dollar in the last 30 days (19.57 → 21.31 per USD). That hurts margins on peso invoices, and on open Mexican receivables.
6. **International customs holds:** a few international customer orders are held for missing documents, with Export Desk cases open.
7. **Overdue dealer invoices:** some with Billing follow-up cases in progress.
8. **Seasonal and regional demand:**
   - Batteries spike in northern winters.
   - AC compressors and radiators sell in hot states in summer.
   - Suspension parts sell more in road-salt states, with an extra bump in spring pothole season.
   - Air filters sell more in dusty states.
9. **Aged stock:** slow movers and superseded OEM numbers sitting on shelves for 200+ days.
10. **Core returns:** pending and unreturned cores on alternators, starters, calipers and batteries.

## Example questions the agent should be able to answer

**Inventory**
- How many front brake pads for a 2019 Ferra Motors Nivo do we have available, and where?
- What's on hand, in transit, sold last month and missing for the Brakes group, by region?
- Which warehouse has the most missing stock, and in which categories?
- What's the aftermarket equivalent of OEM part X, and do we have it?

**International, currency and customs**
- What did we sell to Canada last quarter, in CAD and in USD?
- What's a Toronto customer's total for part X, including GST and shipping?
- How much do Mexican dealers owe us, and what's the exchange loss so far?
- What's held in customs right now, and when was it supposed to arrive (local time)?

**Prices and shipping**
- How much is a front strut for a 2020 Torvik, and what does shipping cost with Parcelora, Velocair and Postara to Phoenix?
- What's the cheapest way to get a bumper cover to Dallas, and when would it arrive?
- Can I get a battery shipped overnight? (No: ground only, and the bot explains why.)
- Total in Canadian dollars for two struts to Toronto, including GST?

**Live support**
- I need to talk to someone about a customs hold. Who do I call, and are they open right now in Riyadh time?
- Which support cases are still open, and who has them?
- The bot can't answer after two tries, so it connects the customer with a person and links the FAQ.

## Swapping in real data later

Keep the same table and column names, and the agent's tools and prompts keep working.
- **Vehicles and VINs:** NHTSA's free vPIC API can fill `vehicles`.
- **Fitment:** usually comes from your suppliers' catalogs. Check their license terms.
- **Exchange rates:** load real ones into `exchange_rates`.
- **Company details:** replace `company` and `support_departments` with your real contact details.
